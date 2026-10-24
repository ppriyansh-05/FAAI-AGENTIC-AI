"""Agentic State Machine Orchestrator for AccessAble AI.

Coordinates the multi-agent workflow:
- Agent 0: Planner (evaluates input, selects scan mode, configures constraints)
- Agent 1: Scanner (DOM Scanner or Playwright/Axe-Core Engine)
- Agent 2: WCAG Standards Analyst (enriches with normative criteria and impact)
- Agent 3: Remediation Agent (synthesizes adaptive context-aware patches)
- Agent 4: Critic & Validation Agent (deterministic retest, regression checks, adaptive retry loops)
"""
from __future__ import annotations

from typing import Any, Optional

from core.models import AuditState, Finding, RemediationResult, CriticRetryRecord
from core.scanner import EnhancedAccessibilityScanner
from core.browser_scanner import run_browser_audit
from core.remediation import SandboxRetestEngine, compute_unified_diff
from core.security import validate_audit_url
from core.gemini_critic import evaluate_remediations_with_gemini, is_gemini_available


class AgentOrchestrator:
    """Manages state transitions, agent invocations, and adaptive critic retries."""

    def __init__(self, state: AuditState) -> None:
        self.state = state

    def run(self) -> AuditState:
        # Step 0: Planner Agent
        self._step_planner()
        if self.state.status == "error":
            return self.state

        # Step 1: Scanner Agent
        self._step_scanner()
        if self.state.status == "error":
            return self.state

        # Step 2: Standards Analyst Agent
        self._step_standards_analyst()

        # Step 3 & 4: Adaptive Remediation & Critic Retest Loop
        self._step_remediation_and_critic_loop()

        # Step 5: Final Human Boundary & Export Packaging
        self._step_finalize()

        return self.state

    def _step_planner(self) -> None:
        self.state.status = "planning"
        self.state.log_agent_step("Planner", "Initialize Plan", "Assessing target and deciding execution strategy.")

        if not self.state.raw_html and not self.state.target_url:
            self.state.status = "error"
            self.state.error_message = "No HTML content or URL provided for audit."
            return

        if self.state.target_url:
            valid, msg = validate_audit_url(self.state.target_url)
            if not valid:
                self.state.status = "error"
                self.state.error_message = f"Security Violation: {msg}"
                self.state.log_agent_step("Planner", "Security Block", msg)
                return

        checks = ["IMG_ALT", "FORM_LABEL", "COLOR_CONTRAST", "PAGE_LANG", "PAGE_TITLE", "HEADING_ORDER", "LINK_DISCERNIBLE"]
        engine_mode = "Playwright + Axe-Core" if self.state.use_browser else "High-Precision Python DOM Engine"

        self.state.plan = {
            "checks": checks,
            "engine": engine_mode,
            "max_retries": self.state.max_retries,
            "strategy": "Dual-pass deterministic scanning with adaptive sandboxed patch re-evaluation.",
        }
        self.state.log_agent_step("Planner", "Plan Approved", f"Running with {engine_mode}. Targeted rules: {len(checks)}")

    def _step_scanner(self) -> None:
        self.state.status = "scanning"
        self.state.log_agent_step("Scanner", "Execute Scan", f"Initiating scan via {self.state.plan.get('engine')}")

        findings: list[Finding] = []

        if self.state.use_browser:
            try:
                target = self.state.target_url if self.state.target_url else self.state.raw_html
                is_url = bool(self.state.target_url)
                axe_findings, rendered_dom, meta = run_browser_audit(target, is_url=is_url)
                if rendered_dom:
                    self.state.raw_html = rendered_dom

                findings.extend(axe_findings)
                self.state.plan["actual_engine"] = "Playwright + Axe-Core"
                self.state.log_agent_step("Scanner", "Browser Axe Scan Complete", f"Captured {len(axe_findings)} axe-core violations.")
            except Exception as exc:
                self.state.plan["actual_engine"] = "Python DOM Fallback (Browser Failed)"
                self.state.plan["browser_error"] = str(exc)
                self.state.log_agent_step("Scanner", "Browser Fallback Triggered", f"Browser audit failed: {exc}. Resorted to static Python DOM inspection.")
                scanner = EnhancedAccessibilityScanner(self.state.raw_html)
                findings = scanner.scan_all()
        else:
            self.state.plan["actual_engine"] = "High-Precision Python DOM Engine"
            scanner = EnhancedAccessibilityScanner(self.state.raw_html)
            findings = scanner.scan_all()
            self.state.log_agent_step("Scanner", "Static DOM Scan Complete", f"Identified {len(findings)} potential barrier signals.")

        deduped: list[Finding] = []
        seen = set()
        for f in findings:
            key = (f.rule_id, f.evidence[:80])
            if key not in seen:
                seen.add(key)
                deduped.append(f)

        self.state.findings = deduped

    def _step_standards_analyst(self) -> None:
        self.state.status = "analyzing"
        self.state.log_agent_step("Standards Analyst", "WCAG Mapping", "Cross-referencing findings against W3C WCAG 2.2 Success Criteria.")

        wcag_standards = {
            "IMG_ALT": ("WCAG 2.2 — 1.1.1 Non-text Content (Level A)", "All non-text content presented to the user has a text alternative that serves equivalent purpose."),
            "FORM_LABEL": ("WCAG 2.2 — 1.3.1 Info and Relationships (Level A) / 3.3.2 Labels or Instructions", "Labels or instructions are provided when content requires user input."),
            "COLOR_CONTRAST": ("WCAG 2.2 — 1.4.3 Contrast (Minimum) (Level AA)", "The visual presentation of text and images of text has a contrast ratio of at least 4.5:1 (3:1 for large text)."),
            "PAGE_LANG": ("WCAG 2.2 — 3.1.1 Language of Page (Level A)", "The default human language of each Web page can be programmatically determined."),
            "PAGE_TITLE": ("WCAG 2.2 — 2.4.2 Page Titled (Level A)", "Web pages have titles that describe topic or purpose."),
            "HEADING_ORDER": ("WCAG 2.2 — 1.3.1 Info and Relationships (Level A)", "Headings communicate the organization of the content on the page."),
            "LINK_DISCERNIBLE": ("WCAG 2.2 — 2.4.4 Link Purpose (In Context) (Level A)", "The purpose of each link can be determined from the link text alone or from the link text together with programmatic context."),
        }

        for finding in self.state.findings:
            if finding.rule_id in wcag_standards:
                criterion, rationale = wcag_standards[finding.rule_id]
                finding.wcag_criterion = criterion
                if not finding.why_it_matters.startswith("WCAG"):
                    finding.why_it_matters = f"{criterion}. {finding.why_it_matters}"

        self.state.log_agent_step("Standards Analyst", "Mapping Completed", f"Successfully mapped {len(self.state.findings)} findings.")

    def _step_remediation_and_critic_loop(self) -> None:
        """Genuinely adaptive remediation and critic verification loop.

        Each retry synthesizes an alternative candidate strategy based on failure feedback.
        """
        self.state.status = "remediating"
        self.state.log_agent_step("Remediation", "Patch Generation", "Synthesizing contextual code fixes for identified violations.")

        if not self.state.findings:
            self.state.log_agent_step("Remediation", "Bypass", "Zero findings reported; skipping remediation cycle.")
            return

        retest_engine = SandboxRetestEngine(self.state.raw_html)

        current_working_html = self.state.raw_html

        while self.state.critic_iteration < self.state.max_retries:
            self.state.critic_iteration += 1
            attempt = self.state.critic_iteration

            self.state.log_agent_step(
                "Critic",
                f"Evaluation Iteration {attempt}",
                f"Executing retest pass using adaptive strategy tier {attempt}."
            )

            # Apply candidate fixes using strategy tier 'attempt'
            patched_html, remediations, retry_records = retest_engine.verify_remediations(
                self.state.findings,
                attempt_number=attempt,
            )

            self.state.remediations = remediations
            self.state.patched_html = patched_html
            self.state.retry_history.extend(retry_records)

            # Gemini Critic integration (Reviews fix quality, WCAG alignment, gives feedback)
            if is_gemini_available():
                self.state.log_agent_step(
                    "Gemini Critic",
                    f"LLM Evaluation Pass {attempt}",
                    f"Gemini Critic reviewing {len(remediations)} candidate fixes for WCAG 2.2 alignment."
                )
                evaluate_remediations_with_gemini(remediations, self.state.findings)

            verified_fixes = [r for r in remediations if r.retest_resolved]
            failed_fixes = [r for r in remediations if not r.retest_resolved]

            critic_note = (
                f"Critic check passed: Iteration {attempt}: {len(verified_fixes)} fixes verified cleanly; "
                f"{len(failed_fixes)} require manual human review or refinement."
            )
            self.state.critic_notes.append(critic_note)

            # If all remediable items are verified or we reached the configured max retries, exit cleanly
            if not failed_fixes or attempt >= self.state.max_retries:
                self.state.log_agent_step(
                    "Critic",
                    "Validation Concluded",
                    f"Critic loop finalized at iteration {attempt}. Verified: {len(verified_fixes)}/{len(remediations)}."
                )
                break
            else:
                self.state.log_agent_step(
                    "Critic",
                    "Adaptive Retry Triggered",
                    f"Critic rejected {len(failed_fixes)} fixes. Switching to alternative candidate strategies for attempt {attempt + 1}."
                )

        if self.state.patched_html and self.state.patched_html != self.state.raw_html:
            self.state.diff = compute_unified_diff(self.state.raw_html, self.state.patched_html)

    def _step_finalize(self) -> None:
        self.state.status = "complete"
        self.state.human_checks = [
            "Verify all image descriptions convey equivalent meaning rather than literal file names.",
            "Verify complete keyboard navigability (Tab key focus order, visible focus rings, Escape handling).",
            "Verify that contrast adheres to dynamic focus and hover state transitions.",
            "Ensure reading order and landmark structure are logical in screen reader testing.",
        ]
        self.state.log_agent_step("Validation Agent", "Human Checklist Generated", "Flagged 4 essential human-in-the-loop audit checkpoints.")
