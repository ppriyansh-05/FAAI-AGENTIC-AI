"""Enhanced remediation engine supporting adaptive multi-strategy patch synthesis and sandbox testing."""
from __future__ import annotations

import difflib
import hashlib
import re
from typing import Any, Optional
from bs4 import BeautifulSoup

from core.models import Finding, RemediationCandidate, RemediationResult, CriticRetryRecord
from core.scanner import EnhancedAccessibilityScanner


def compute_unified_diff(original: str, modified: str, filename: str = "audited_page.html") -> str:
    """Generates standard unified diff between original and patched HTML."""
    orig_lines = original.splitlines(keepends=True)
    mod_lines = modified.splitlines(keepends=True)
    diff = difflib.unified_diff(orig_lines, mod_lines, fromfile=f"a/{filename}", tofile=f"b/{filename}")
    return "".join(diff)


class AdaptiveRemediationSynthesizer:
    """Synthesizes alternative candidate strategies for a finding."""

    @staticmethod
    def get_candidate_strategies(finding: Finding, soup: BeautifulSoup, attempt: int) -> list[RemediationCandidate]:
        rule = finding.rule_id
        candidates: list[RemediationCandidate] = []

        if rule == "PAGE_LANG":
            html_tag = soup.find("html")
            if html_tag:
                orig = str(html_tag)
                open_match = re.search(r"<html[^>]*>", orig, re.I)
                if open_match:
                    tag_str = open_match.group(0)
                    # Attempt 1: Standard 'en'
                    # Attempt 2: BCP-47 fallback with dir='ltr' attribute
                    if attempt == 1:
                        new_tag = re.sub(r'lang=["\'][^"\']*["\']', 'lang="en"', tag_str, flags=re.I) if "lang=" in tag_str.lower() else tag_str.replace("<html", '<html lang="en"')
                        candidates.append(RemediationCandidate(
                            candidate_id=f"lang_cand_{attempt}",
                            strategy_name="primary_lang_en",
                            target_rule="PAGE_LANG",
                            original_snippet=tag_str,
                            proposed_snippet=new_tag,
                            rationale="Declare standard English document language.",
                        ))
                    else:
                        new_tag = tag_str.replace("<html", '<html lang="en" dir="ltr"')
                        candidates.append(RemediationCandidate(
                            candidate_id=f"lang_cand_{attempt}",
                            strategy_name="lang_with_text_direction",
                            target_rule="PAGE_LANG",
                            original_snippet=tag_str,
                            proposed_snippet=new_tag,
                            rationale="Declare document language with explicit text direction.",
                        ))

        elif rule == "PAGE_TITLE":
            head_tag = soup.find("head")
            title_tag = soup.find("title")
            if title_tag:
                orig = str(title_tag)
                if attempt == 1:
                    prop = "<title>Accessible Web Experience | AccessAble AI</title>"
                else:
                    prop = "<title>Home — Customer Portal & Services</title>"
                candidates.append(RemediationCandidate(
                    candidate_id=f"title_cand_{attempt}",
                    strategy_name="descriptive_title_header",
                    target_rule="PAGE_TITLE",
                    original_snippet=orig,
                    proposed_snippet=prop,
                    rationale="Add descriptive title tag inside head.",
                ))
            elif head_tag:
                candidates.append(RemediationCandidate(
                    candidate_id=f"title_cand_{attempt}",
                    strategy_name="insert_into_head",
                    target_rule="PAGE_TITLE",
                    original_snippet="<head>",
                    proposed_snippet="<head>\n  <title>Accessible Web Experience | AccessAble AI</title>",
                    rationale="Inject title inside existing head block.",
                ))

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
                # Strategy 1: Contextual informative alt description
                # Strategy 2: If previous attempt rejected or failed, synthesize clean decorative alt="" or aria-label
                if attempt == 1:
                    prop = orig.replace("<img", '<img alt="[PROPOSED: Describe image context]"')
                    candidates.append(RemediationCandidate(
                        candidate_id=f"img_cand_{attempt}",
                        strategy_name="informative_alt_placeholder",
                        target_rule="IMG_ALT",
                        original_snippet=orig,
                        proposed_snippet=prop,
                        rationale="Provide informative text alternative description.",
                        uncertainty_notes="Image content and visual meaning cannot be established automatically. Human review is required to supply accurate description.",
                    ))
                else:
                    prop = orig.replace("<img", '<img alt="" role="presentation"')
                    candidates.append(RemediationCandidate(
                        candidate_id=f"img_cand_{attempt}",
                        strategy_name="decorative_presentation_fallback",
                        target_rule="IMG_ALT",
                        original_snippet=orig,
                        proposed_snippet=prop,
                        rationale="Mark non-essential image as decorative per WCAG H67.",
                        uncertainty_notes="Only select if the image is purely decorative, redundant, or purely stylistic.",
                    ))

        elif rule == "FORM_LABEL":
            id_match = re.search(r'id=["\']([^"\']+)["\']', finding.evidence)
            name_match = re.search(r'name=["\']([^"\']+)["\']', finding.evidence)
            target_id = id_match.group(1) if id_match else (name_match.group(1) if name_match else "input_field")

            for el in soup.find_all(["input", "select", "textarea"]):
                if (id_match and el.get("id") == target_id) or (name_match and el.get("name") == target_id):
                    orig = str(el)
                    if attempt == 1:
                        # Strategy 1: Explicit <label for="id">
                        if not el.get("id"):
                            el["id"] = target_id
                        prop = f'<label for="{target_id}">Enter {target_id.capitalize()}</label>\n{str(el)}'
                        candidates.append(RemediationCandidate(
                            candidate_id=f"label_cand_{attempt}",
                            strategy_name="explicit_for_label",
                            target_rule="FORM_LABEL",
                            original_snippet=orig,
                            proposed_snippet=prop,
                            rationale="Insert explicit <label for> element preceding input.",
                        ))
                    else:
                        # Strategy 2 (adaptive retry): Direct programmatic aria-label attribute
                        if "<input" in orig:
                            prop = orig.replace("<input", f'<input aria-label="{target_id.capitalize()}"')
                        elif "<select" in orig:
                            prop = orig.replace("<select", f'<select aria-label="{target_id.capitalize()}"')
                        else:
                            prop = orig.replace("<textarea", f'<textarea aria-label="{target_id.capitalize()}"')
                        candidates.append(RemediationCandidate(
                            candidate_id=f"label_cand_{attempt}",
                            strategy_name="programmatic_aria_label",
                            target_rule="FORM_LABEL",
                            original_snippet=orig,
                            proposed_snippet=prop,
                            rationale="Attach inline accessible aria-label to form control.",
                        ))

        elif rule == "COLOR_CONTRAST":
            style_match = re.search(r'style=["\']([^"\']+)["\']', finding.evidence)
            if style_match:
                orig_style = style_match.group(0)
                # Strategy 1: High-contrast slate #111827 (luminance ~0.01)
                # Strategy 2: Absolute pure black #000000 (21:1 on white)
                color_target = "#111827" if attempt == 1 else "#000000"
                new_style = re.sub(r"color\s*:\s*[^;\"]+", f"color: {color_target}", orig_style, flags=re.I)
                candidates.append(RemediationCandidate(
                    candidate_id=f"contrast_cand_{attempt}",
                    strategy_name=f"contrast_enhancement_{color_target}",
                    target_rule="COLOR_CONTRAST",
                    original_snippet=finding.evidence,
                    proposed_snippet=finding.evidence.replace(orig_style, new_style),
                    rationale=f"Substitute low-contrast text color with {color_target}.",
                ))

        elif rule == "HEADING_ORDER":
            match = re.search(r"<(h[1-6])([^>]*)>(.*?)</\1>", finding.evidence, re.DOTALL | re.I)
            if match:
                orig_full = match.group(0)
                # Parse level
                cur_lvl = int(match.group(1)[1])
                target_lvl = max(1, cur_lvl - 1) if attempt == 1 else 2
                prop = orig_full.replace(f"<h{cur_lvl}", f"<h{target_lvl}").replace(f"</h{cur_lvl}>", f"</h{target_lvl}>")
                candidates.append(RemediationCandidate(
                    candidate_id=f"heading_cand_{attempt}",
                    strategy_name="sequential_heading_step",
                    target_rule="HEADING_ORDER",
                    original_snippet=orig_full,
                    proposed_snippet=prop,
                    rationale="Adjust heading tag level to prevent skipping.",
                ))

        elif rule == "LINK_DISCERNIBLE":
            orig = finding.evidence
            if "></a>" in orig:
                text = "View details" if attempt == 1 else "Learn more about our services"
                candidates.append(RemediationCandidate(
                    candidate_id=f"link_cand_{attempt}",
                    strategy_name="meaningful_anchor_text",
                    target_rule="LINK_DISCERNIBLE",
                    original_snippet=orig,
                    proposed_snippet=orig.replace("></a>", f">{text}</a>"),
                    rationale="Insert meaningful descriptive text inside empty anchor.",
                ))

        return candidates


class SandboxRetestEngine:
    """Isolated retesting engine that applies candidates and verifies resolution with zero regressions."""

    def __init__(self, raw_html: str) -> None:
        self.raw_html = raw_html

    def verify_remediations(
        self,
        findings: list[Finding],
        attempt_number: int = 1,
    ) -> tuple[str, list[RemediationResult], list[CriticRetryRecord]]:
        current_html = self.raw_html
        results: list[RemediationResult] = []
        retry_records: list[CriticRetryRecord] = []

        baseline_scanner = EnhancedAccessibilityScanner(self.raw_html)
        baseline_findings = baseline_scanner.scan_all()
        baseline_count_by_rule = {
            r: len([f for f in baseline_findings if f.rule_id == r])
            for r in {f.rule_id for f in baseline_findings}
        }
        baseline_rule_set = set(baseline_count_by_rule.keys())

        for finding in findings:
            soup = BeautifulSoup(current_html, "html.parser")
            candidates = AdaptiveRemediationSynthesizer.get_candidate_strategies(finding, soup, attempt=attempt_number)

            if not candidates:
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

            chosen_cand = candidates[0]
            orig_str = chosen_cand.original_snippet
            new_str = chosen_cand.proposed_snippet

            if orig_str not in current_html:
                results.append(RemediationResult(
                    finding_id=finding.id,
                    rule_id=finding.rule_id,
                    original_snippet=orig_str,
                    proposed_snippet=new_str,
                    status="needs_human_approval",
                    diff="",
                    retest_resolved=False,
                    critic_notes="Original code snippet could not be matched uniquely in current working document.",
                    strategy_used=chosen_cand.strategy_name,
                    candidate_id=chosen_cand.candidate_id,
                ))
                continue

            test_html = current_html.replace(orig_str, new_str, 1)

            retest_scanner = EnhancedAccessibilityScanner(test_html)
            retest_findings = retest_scanner.scan_all()
            retest_count_by_rule = {
                r: len([f for f in retest_findings if f.rule_id == r])
                for r in {f.rule_id for f in retest_findings}
            }
            retest_rule_set = set(retest_count_by_rule.keys())

            rule = finding.rule_id
            is_resolved = retest_count_by_rule.get(rule, 0) < baseline_count_by_rule.get(rule, 1)
            new_regressions = list(retest_rule_set - baseline_rule_set)

            record = CriticRetryRecord(
                iteration=attempt_number,
                candidate_id=chosen_cand.candidate_id,
                reason="Verification scan evaluation",
                critic_feedback="Passed with zero regressions" if is_resolved and not new_regressions else f"Unresolved or introduced: {new_regressions}",
                changed_action=f"Applied strategy '{chosen_cand.strategy_name}': {chosen_cand.rationale}",
                before_finding_count=len(baseline_findings),
                after_finding_count=len(retest_findings),
                regressions_detected=new_regressions,
                resolved=is_resolved and not new_regressions,
            )
            retry_records.append(record)

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
                    critic_notes=f"Verified cleanly via strategy '{chosen_cand.strategy_name}'.",
                    strategy_used=chosen_cand.strategy_name,
                    candidate_id=chosen_cand.candidate_id,
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
                    critic_notes=f"Candidate strategy '{chosen_cand.strategy_name}' failed verification.",
                    strategy_used=chosen_cand.strategy_name,
                    candidate_id=chosen_cand.candidate_id,
                ))

        return current_html, results, retry_records
