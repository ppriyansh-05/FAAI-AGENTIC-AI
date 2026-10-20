"""Backward compatibility bridge for legacy CA-3 imports and functions."""
from __future__ import annotations

from typing import Any
from core.models import Finding, AuditState
from core.orchestrator import AgentOrchestrator
from core.scanner import calculate_contrast_ratio, EnhancedAccessibilityScanner

RULES = ("IMG_ALT", "FORM_LABEL", "PAGE_LANG", "PAGE_TITLE", "COLOR_CONTRAST", "HEADING_ORDER", "LINK_DISCERNIBLE")


def contrast_ratio(foreground: str, background: str) -> float | None:
    return calculate_contrast_ratio(foreground, background)


def planner_agent(html: str) -> dict[str, Any]:
    if not isinstance(html, str) or not html.strip():
        return {"status": "no_input", "checks": [], "message": "Paste HTML before running an audit."}
    return {
        "status": "ready",
        "checks": list(RULES),
        "message": "Run supported deterministic accessibility checks, then enrich and validate the findings.",
    }


def findings_to_rows(findings: list[Finding]) -> list[dict[str, Any]]:
    return [finding.to_dict() for finding in findings]


def run_audit(html: str, use_browser: bool = False, target_url: str | None = None) -> dict[str, Any]:
    """Preserves original function signature while powering the modern agent orchestrator."""
    if not isinstance(html, str) or (not html.strip() and not target_url):
        return {
            "status": "no_input",
            "message": "Paste HTML or provide a valid URL before running an audit.",
            "plan": {"checks": []},
            "findings": [],
            "counts": {"High": 0, "Medium": 0, "Low": 0},
            "human_checks": [],
            "critic_notes": [],
            "diff": "",
            "patched_html": None,
            "agent_trace": [],
        }

    state = AuditState(
        input_source="public_url" if target_url else "raw_html",
        raw_html=html,
        target_url=target_url,
        use_browser=use_browser,
    )

    orchestrator = AgentOrchestrator(state)
    result_state = orchestrator.run()

    if result_state.status == "error":
        return {
            "status": "error",
            "message": result_state.error_message or "Audit encountered an unexpected failure.",
            "plan": result_state.plan,
            "findings": [],
            "counts": {"High": 0, "Medium": 0, "Low": 0},
            "human_checks": [],
            "critic_notes": result_state.critic_notes,
            "diff": "",
            "patched_html": None,
            "agent_trace": result_state.agent_trace,
        }

    counts = {level: sum(item.severity == level for item in result_state.findings) for level in ("High", "Medium", "Low")}

    return {
        "status": "complete",
        "message": "Audit completed successfully.",
        "plan": result_state.plan,
        "findings": result_state.findings,
        "remediations": result_state.remediations,
        "counts": counts,
        "human_checks": result_state.human_checks,
        "critic_notes": result_state.critic_notes,
        "diff": result_state.diff,
        "patched_html": result_state.patched_html,
        "agent_trace": result_state.agent_trace,
    }
