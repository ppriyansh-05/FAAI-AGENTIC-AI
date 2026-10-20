"""Playwright and axe-core browser scanning integration with safety isolation."""
from __future__ import annotations

import json
from typing import Any
from playwright.sync_api import sync_playwright, Error as PlaywrightError

from core.models import Finding
from core.security import validate_audit_url, MAX_TIMEOUT_SECONDS

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
        # Launch isolated browser instance without credentials or external extensions
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="AccessAbleAI-Auditor/1.0 (Accessibility Bot)",
            bypass_csp=True,
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()
        page.set_default_timeout(int(MAX_TIMEOUT_SECONDS * 1000))

        try:
            if is_url:
                response = page.goto(target, wait_until="networkidle", timeout=int(MAX_TIMEOUT_SECONDS * 1000))
                metadata["http_status"] = response.status if response else None
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
                # Map impact to Severity
                severity_map = {"critical": "High", "serious": "High", "moderate": "Medium", "minor": "Low"}
                severity = severity_map.get(impact, "Medium")
                description = v.get("description", "")
                help_url = v.get("helpUrl", "")

                wcag_info, mapped_rule = AXE_WCAG_MAPPING.get(rule_id, (f"Axe rule: {rule_id}", rule_id.upper()))

                # Extract affected nodes
                nodes = v.get("nodes", [])
                for node_idx, node in enumerate(nodes[:5]):  # Cap at 5 representative nodes
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
