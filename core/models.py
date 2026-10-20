"""Structured types and data contracts for AccessAble AI multi-agent auditor."""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Any, Optional


class Severity(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class EngineType(str, Enum):
    CUSTOM_PYTHON = "custom_python"
    AXE_CORE = "axe_core"


class ValidationStatus(str, Enum):
    DETECTED = "detected"
    VERIFIED_FIXED = "verified_fixed"
    UNRESOLVED = "unresolved"
    REGRESSION = "regression"
    INCONCLUSIVE = "inconclusive"


class CriticDecisionType(str, Enum):
    ACCEPT = "accept"
    RETRY_REMEDIATION = "retry_remediation"
    ESCALATE_HUMAN = "escalate_human"
    STOP_MAX_RETRIES = "stop_max_retries"


@dataclass
class Finding:
    id: str  # Unique finding identifier e.g. finding_img_alt_1
    rule_id: str  # e.g. IMG_ALT, FORM_LABEL, COLOR_CONTRAST, PAGE_LANG, PAGE_TITLE
    severity: str  # "High", "Medium", "Low"
    title: str  # Brief summary of the violation
    evidence: str  # Exact HTML element snippet or rendered style representation
    why_it_matters: str  # Practical impact on assistive tech users
    automated: bool  # True if detected programmatically
    element_tag: str = ""  # e.g. "img", "input", "html"
    selector: str = ""  # CSS selector or unique identifier where available
    wcag_criterion: str = ""  # e.g. "WCAG 2.2 — 1.1.1 Non-text Content (Level A)"
    recommendation: str = ""  # Actionable implementation guidance
    remediation_patch: Optional[str] = None  # Proposed concrete replacement snippet
    validation: str = ""  # What was tested vs what requires manual verification
    requires_human_review: bool = True  # True if contextual judgment is needed
    confidence: float = 1.0  # Detection certainty score (0.0 to 1.0)
    engine: str = "custom_python"  # "custom_python" | "axe_core"
    validation_status: str = "detected"  # "detected" | "verified_fixed" | "unresolved" | "regression" | "inconclusive"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RemediationCandidate:
    candidate_id: str
    strategy_name: str
    target_rule: str
    original_snippet: str
    proposed_snippet: str
    rationale: str
    uncertainty_notes: Optional[str] = None


@dataclass
class RemediationResult:
    finding_id: str
    rule_id: str
    original_snippet: str
    proposed_snippet: str
    status: str  # "applied_and_verified" | "needs_human_approval" | "failed_validation" | "rejected"
    diff: str = ""
    retest_resolved: bool = False
    critic_notes: str = ""
    strategy_used: str = "standard_replacement"
    candidate_id: str = ""


@dataclass
class CriticRetryRecord:
    iteration: int
    candidate_id: str
    reason: str
    critic_feedback: str
    changed_action: str
    before_finding_count: int
    after_finding_count: int
    regressions_detected: list[str] = field(default_factory=list)
    resolved: bool = False


@dataclass
class AuditState:
    input_source: str  # "pasted_html", "sample_page", "uploaded_file", "public_url"
    raw_html: str
    target_url: Optional[str] = None
    use_browser: bool = False
    plan: dict[str, Any] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    remediations: list[RemediationResult] = field(default_factory=list)
    retry_history: list[CriticRetryRecord] = field(default_factory=list)
    patched_html: Optional[str] = None
    diff: str = ""
    critic_iteration: int = 0
    max_retries: int = 3
    critic_notes: list[str] = field(default_factory=list)
    human_checks: list[str] = field(default_factory=list)
    status: str = "initialized"  # "initialized", "planning", "scanning", "analyzing", "remediating", "validating", "complete", "error"
    error_message: Optional[str] = None
    agent_trace: list[dict[str, Any]] = field(default_factory=list)

    def log_agent_step(self, agent_name: str, action: str, details: str) -> None:
        self.agent_trace.append({
            "agent": agent_name,
            "action": action,
            "details": details,
        })
