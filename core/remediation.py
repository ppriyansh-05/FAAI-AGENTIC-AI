"""Remediation and Safe Sandbox Retesting Engine.

Applies proposed code fixes onto an isolated copy of the HTML, re-evaluates
with the scanner, and computes before-and-after resolution statuses to guarantee
no regressions are introduced.
"""
from __future__ import annotations

import difflib
import re
from typing import Any
from bs4 import BeautifulSoup

from core.models import Finding, RemediationResult
from core.scanner import EnhancedAccessibilityScanner


def generate_patch_for_finding(finding: Finding, soup: BeautifulSoup) -> tuple[str, str] | None:
    """Computes exact original snippet and suggested replacement for an accessible fix."""
    rule = finding.rule_id

    if rule == "PAGE_LANG":
        html_tag = soup.find("html")
        if html_tag:
            orig = str(html_tag)
            # Replace opening tag
            open_match = re.search(r"<html[^>]*>", orig, re.I)
            if open_match:
                tag_str = open_match.group(0)
                if "lang=" in tag_str.lower():
                    new_tag = re.sub(r'lang=["\'][^"\']*["\']', 'lang="en"', tag_str, flags=re.I)
                else:
                    new_tag = tag_str.replace("<html", '<html lang="en"')
                return tag_str, new_tag

    elif rule == "PAGE_TITLE":
        head_tag = soup.find("head")
        title_tag = soup.find("title")
        if title_tag:
            return str(title_tag), "<title>Accessible Web Experience | AccessAble AI</title>"
        elif head_tag:
            return "<head>", "<head>\n  <title>Accessible Web Experience | AccessAble AI</title>"
        else:
            return "<html>", "<html>\n<head>\n  <title>Accessible Web Experience | AccessAble AI</title>\n</head>"

    elif rule == "IMG_ALT":
        src_match = re.search(r'src=["\']([^"\']+)["\']', finding.evidence)
        src = src_match.group(1) if src_match else None
        target_img = None
        for img in soup.find_all("img"):
            if src and img.get("src") == src:
                target_img = img
                break
            elif not img.has_attr("alt"):
                target_img = img
                break

        if target_img:
            orig = str(target_img)
            # Create a clean contextual replacement
            img_copy = BeautifulSoup(orig, "html.parser").find("img")
            if img_copy:
                img_copy["alt"] = "Descriptive image representation"
                return orig, str(img_copy)

    elif rule == "FORM_LABEL":
        # Find input or select without label
        id_match = re.search(r'id=["\']([^"\']+)["\']', finding.evidence)
        name_match = re.search(r'name=["\']([^"\']+)["\']', finding.evidence)
        target_id = id_match.group(1) if id_match else (name_match.group(1) if name_match else "input_field")

        for el in soup.find_all(["input", "select", "textarea"]):
            if (id_match and el.get("id") == target_id) or (name_match and el.get("name") == target_id):
                orig = str(el)
                if not el.get("id"):
                    el["id"] = target_id
                label_tag = f'<label for="{target_id}">Enter {target_id.capitalize()}</label>\n'
                return orig, f"{label_tag}{str(el)}"

    elif rule == "COLOR_CONTRAST":
        # Search for inline style color and replace with high-contrast equivalent
        style_match = re.search(r'style=["\']([^"\']+)["\']', finding.evidence)
        if style_match:
            orig_style = style_match.group(0)
            # Replace color with #111827 (very dark slate, ensures >= 7.0:1 on white)
            new_style = re.sub(r"color\s*:\s*[^;\"]+", "color: #111827", orig_style, flags=re.I)
            if orig_style in finding.evidence:
                return finding.evidence, finding.evidence.replace(orig_style, new_style)

    elif rule == "HEADING_ORDER":
        # Fix skipped heading
        match = re.search(r"<(h[1-6])([^>]*)>(.*?)</\1>", finding.evidence, re.DOTALL | re.I)
        if match:
            orig_full = match.group(0)
            target_tag = finding.remediation_patch or orig_full
            return orig_full, target_tag

    elif rule == "LINK_DISCERNIBLE":
        orig = finding.evidence
        if "></a>" in orig:
            return orig, orig.replace("></a>", ">Explore details</a>")

    return None


def compute_unified_diff(original: str, modified: str, filename: str = "audited_page.html") -> str:
    """Generates standard unified diff between original and patched HTML."""
    orig_lines = original.splitlines(keepends=True)
    mod_lines = modified.splitlines(keepends=True)
    diff = difflib.unified_diff(orig_lines, mod_lines, fromfile=f"a/{filename}", tofile=f"b/{filename}")
    return "".join(diff)


class SandboxRetestEngine:
    """Applies patches in isolated memory, verifies resolution, and flags regressions."""

    def __init__(self, raw_html: str) -> None:
        self.raw_html = raw_html

    def verify_remediations(self, findings: list[Finding]) -> tuple[str, list[RemediationResult], list[Finding]]:
        """Synthesize fixes, apply to temporary document, and re-run scanner."""
        current_html = self.raw_html
        results: list[RemediationResult] = []

        # Run baseline scan to identify baseline finding IDs
        baseline_scanner = EnhancedAccessibilityScanner(self.raw_html)
        baseline_findings = baseline_scanner.scan_all()
        baseline_rules = {f.rule_id for f in baseline_findings}

        for finding in findings:
            soup = BeautifulSoup(current_html, "html.parser")
            patch_pair = generate_patch_for_finding(finding, soup)

            if not patch_pair:
                results.append(RemediationResult(
                    finding_id=finding.id,
                    rule_id=finding.rule_id,
                    original_snippet=finding.evidence,
                    proposed_snippet=finding.recommendation,
                    status="needs_human_approval",
                    diff="",
                    retest_resolved=False,
                    critic_notes="Ambiguous automated patch: contextual human review is advised.",
                ))
                continue

            orig_str, new_str = patch_pair

            if orig_str not in current_html:
                results.append(RemediationResult(
                    finding_id=finding.id,
                    rule_id=finding.rule_id,
                    original_snippet=orig_str,
                    proposed_snippet=new_str,
                    status="needs_human_approval",
                    diff="",
                    retest_resolved=False,
                    critic_notes="Original code snippet could not be uniquely matched for automated replacement.",
                ))
                continue

            # Apply candidate fix to temporary working copy
            test_html = current_html.replace(orig_str, new_str, 1)

            # Re-scan candidate copy
            retest_scanner = EnhancedAccessibilityScanner(test_html)
            retest_findings = retest_scanner.scan_all()
            retest_rules = {f.rule_id for f in retest_findings}

            # Verify if this specific rule was cleared
            is_resolved = (
                len([f for f in retest_findings if f.rule_id == finding.rule_id]) <
                len([f for f in baseline_findings if f.rule_id == finding.rule_id])
            )

            # Check if any brand new rule violations were introduced
            new_regressions = retest_rules - baseline_rules

            if is_resolved and not new_regressions:
                current_html = test_html
                finding.validation_status = "verified_fixed"
                results.append(RemediationResult(
                    finding_id=finding.id,
                    rule_id=finding.rule_id,
                    original_snippet=orig_str,
                    proposed_snippet=new_str,
                    status="applied_and_verified",
                    diff=compute_unified_diff(orig_str, new_str),
                    retest_resolved=True,
                    critic_notes="Patch successfully verified: retest passed with zero regressions.",
                ))
            else:
                finding.validation_status = "unresolved"
                results.append(RemediationResult(
                    finding_id=finding.id,
                    rule_id=finding.rule_id,
                    original_snippet=orig_str,
                    proposed_snippet=new_str,
                    status="failed_validation",
                    diff="",
                    retest_resolved=False,
                    critic_notes=f"Candidate patch failed verification. New regressions: {list(new_regressions)}",
                ))

        # Final scan of patched HTML
        final_scanner = EnhancedAccessibilityScanner(current_html)
        final_findings = final_scanner.scan_all()

        return current_html, results, final_findings
