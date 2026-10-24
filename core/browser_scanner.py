"""Playwright and axe-core browser scanning integration with safety isolation and request guard."""
from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, Error as PlaywrightError, Route

from core.models import Finding
from core.security import validate_audit_url, is_ip_blocked, MAX_TIMEOUT_SECONDS

# AXE rule to WCAG mappings
AXE_WCAG_MAPPING: dict[str, tuple[str, str]] = {
    "image-alt": ("WCAG 2.2 — 1.1.1 Non-text Content (Level A)", "IMG_ALT"),
    "label": ("WCAG 2.2 — 1.3.1 Info and Relationships / 3.3.2 Labels or Instructions (Level A)", "FORM_LABEL"),
    "color-contrast": ("WCAG 2.2 — 1.4.3 Contrast (Minimum) (Level AA)", "COLOR_CONTRAST"),
    "html-has-lang": ("WCAG 2.2 — 3.1.1 Language of Page (Level A)", "PAGE_LANG"),
    "document-title": ("WCAG 2.2 — 2.4.2 Page Titled (Level A)", "PAGE_TITLE"),
    "heading-order": ("WCAG 2.2 — 1.3.1 Info and Relationships (Level A)", "HEADING_ORDER"),
    "link-name": ("WCAG 2.2 — 2.4.4 Link Purpose (In Context) (Level A)", "LINK_DISCERNIBLE"),
    "button-name": ("WCAG 2.2 — 4.1.2 Name, Role, Value (Level A)", "BUTTON_NAME"),
}


def _subresource_security_interceptor(route: Route) -> None:
    """Intercepts all browser subresource requests to prevent subresource SSRF."""
    req_url = route.request.url
    try:
        parsed = urlparse(req_url)
        # Block non-http/https subresources
        if parsed.scheme.lower() not in ("http", "https"):
            route.abort("blockedbyclient")
            return
        # Block subresources targeting localhost or internal hosts
        host = (parsed.hostname or "").lower()
        if host in ("localhost", "127.0.0.1", "::1", "metadata.google.internal") or host.endswith(".local") or host.endswith(".internal"):
            route.abort("blockedbyclient")
            return
        route.continue_()
    except Exception:
        route.abort("blockedbyclient")


def run_browser_audit(target: str, is_url: bool = False) -> tuple[list[Finding], str, dict[str, Any]]:
    """Runs Playwright headless Chromium with axe-core.

    Args:
        target: Raw HTML string or target URL.
        is_url: True if target is a web URL, False if raw HTML.

    Returns:
        tuple of (findings, rendered_html, metadata)
    """
    if is_url:
        valid, msg = validate_audit_url(target)
        if not valid:
            raise ValueError(f"Security validation failed for URL: {msg}")

    findings: list[Finding] = []
    rendered_html = ""
    metadata: dict[str, Any] = {"engine": "playwright_axe_core", "browser": "chromium_headless"}

    try:
        from axe_core_python.sync_playwright import Axe
    except ImportError:
        raise RuntimeError("axe-core-python is not installed. Please install axe-core-python.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="AccessAbleAI-Auditor/1.0 (Accessibility Bot)",
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()
        page.set_default_timeout(int(MAX_TIMEOUT_SECONDS * 1000))

        # Enforce network request guard on subresources
        page.route("**/*", _subresource_security_interceptor)

        try:
            if is_url:
                # Track final response to detect open redirects
                response = page.goto(target, wait_until="domcontentloaded", timeout=min(int(MAX_TIMEOUT_SECONDS * 1000), 20000))
                if response:
                    final_url = response.url
                    # Verify final URL after potential redirects
                    valid_final, final_msg = validate_audit_url(final_url)
                    if not valid_final:
                        raise ValueError(f"Redirect blocked by SSRF guard: {final_msg}")
                    metadata["http_status"] = response.status
                    metadata["final_url"] = final_url
            else:
                page.set_content(target, wait_until="domcontentloaded")

            rendered_html = page.content()

            # Execute Axe
            axe = Axe()
            results = axe.run(page)

            violations = results.get("violations", [])
            for idx, v in enumerate(violations):
                rule_id = v.get("id", "axe_rule")
                impact = v.get("impact", "moderate")
                severity_map = {"critical": "High", "serious": "High", "moderate": "Medium", "minor": "Low"}
                severity = severity_map.get(impact, "Medium")
                description = v.get("description", "")
                help_url = v.get("helpUrl", "")

                wcag_info, mapped_rule = AXE_WCAG_MAPPING.get(rule_id, (f"Axe rule: {rule_id}", rule_id.upper()))

                nodes = v.get("nodes", [])
                for node_idx, node in enumerate(nodes[:5]):
                    target_sel = " > ".join(node.get("target", []))
                    html_snippet = node.get("html", "")
                    failure_summary = node.get("failureSummary", description)

                    findings.append(Finding(
                        id=f"axe_{rule_id}_{idx}_{node_idx}",
                        rule_id=mapped_rule,
                        severity=severity,
                        title=f"{v.get('help', rule_id)}",
                        evidence=html_snippet or target_sel,
                        why_it_matters=f"{wcag_info}. {description}",
                        automated=True,
                        selector=target_sel,
                        wcag_criterion=wcag_info,
                        recommendation=f"{failure_summary}. See reference: {help_url}",
                        validation="Automated Axe-Core DOM inspection.",
                        requires_human_review=True,
                        confidence=0.98,
                        engine="axe_core",
                    ))

            metadata["axe_violations_count"] = len(violations)
            metadata["axe_passes_count"] = len(results.get("passes", []))

        finally:
            context.close()
            browser.close()

    return findings, rendered_html, metadata
