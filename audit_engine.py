"""Deterministic accessibility-audit agents used by the AccessAble AI PoC.

The checks are intentionally transparent and rule based: this makes the demo
repeatable and avoids presenting a mock LLM as an authoritative accessibility
expert.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from html.parser import HTMLParser
import re
from typing import Any


@dataclass
class Finding:
    rule_id: str
    severity: str
    title: str
    evidence: str
    why_it_matters: str
    automated: bool
    recommendation: str = ""
    validation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


RULES = ("IMG_ALT", "FORM_LABEL", "PAGE_LANG", "PAGE_TITLE", "COLOR_CONTRAST")


def planner_agent(html: str) -> dict[str, Any]:
    """Agent 0: plans the deterministic checks supported by this PoC.

    The planner does not claim to understand arbitrary websites.  It exposes
    which rule modules will run and returns a safe status for empty input.
    """
    if not isinstance(html, str) or not html.strip():
        return {"status": "no_input", "checks": [], "message": "Paste HTML before running an audit."}
    return {
        "status": "ready",
        "checks": list(RULES),
        "message": "Run the five supported deterministic HTML checks, then enrich and validate the findings.",
    }


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str]]] = []
        self.ids: set[str] = set()
        self.labels_for: set[str] = set()
        self.has_lang = False
        self.title_text = ""
        self._inside_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        self.tags.append((tag.lower(), values))
        if values.get("id"):
            self.ids.add(values["id"])
        if tag.lower() == "html" and values.get("lang"):
            self.has_lang = True
        if tag.lower() == "label" and values.get("for"):
            self.labels_for.add(values["for"])
        self._inside_title = tag.lower() == "title"

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._inside_title = False

    def handle_data(self, data: str) -> None:
        if self._inside_title:
            self.title_text += data.strip()


def _hex_to_rgb(value: str) -> tuple[int, int, int] | None:
    value = value.strip().lower()
    named = {"white": "#ffffff", "black": "#000000", "red": "#ff0000", "blue": "#0000ff", "gray": "#808080", "grey": "#808080", "yellow": "#ffff00"}
    value = named.get(value, value)
    match = re.fullmatch(r"#([0-9a-f]{3}|[0-9a-f]{6})", value)
    if not match:
        return None
    code = match.group(1)
    if len(code) == 3:
        code = "".join(ch * 2 for ch in code)
    return tuple(int(code[index:index + 2], 16) for index in (0, 2, 4))


def _luminance(rgb: tuple[int, int, int]) -> float:
    channels = []
    for number in rgb:
        value = number / 255
        channels.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(foreground: str, background: str) -> float | None:
    fg, bg = _hex_to_rgb(foreground), _hex_to_rgb(background)
    if not fg or not bg:
        return None
    light, dark = max(_luminance(fg), _luminance(bg)), min(_luminance(fg), _luminance(bg))
    return (light + 0.05) / (dark + 0.05)


def scanner_agent(html: str) -> tuple[list[Finding], PageParser]:
    """Agent 1: inspect DOM-like input and emit machine-detectable signals."""
    parser = PageParser()
    parser.feed(html)
    findings: list[Finding] = []
    images = [(tag, attrs) for tag, attrs in parser.tags if tag == "img"]
    for _, attrs in images:
        if "alt" not in attrs or not attrs["alt"].strip():
            findings.append(Finding("IMG_ALT", "High", "Image has no text alternative", f'<img src="{attrs.get("src", "unknown")}">', "People using screen readers may not receive the image's purpose.", True))
    for tag, attrs in parser.tags:
        if tag in {"input", "select", "textarea"} and attrs.get("type") not in {"hidden", "submit", "button", "reset"}:
            accessible_name = attrs.get("id") in parser.labels_for or bool(attrs.get("aria-label") or attrs.get("aria-labelledby") or attrs.get("title"))
            if not accessible_name:
                findings.append(Finding("FORM_LABEL", "High", "Form control has no programmatic label", f"<{tag} name=\"{attrs.get('name', '')}\" id=\"{attrs.get('id', '')}\">", "A screen-reader user may not know what information to enter.", True))
    if not parser.has_lang:
        findings.append(Finding("PAGE_LANG", "Medium", "Page language is not declared", "<html> has no lang attribute", "Assistive technologies may use an incorrect pronunciation rule.", True))
    if not parser.title_text:
        findings.append(Finding("PAGE_TITLE", "Medium", "Page has no descriptive title", "No <title> element found", "The title helps people identify the page and switch between tabs.", True))
    for tag, attrs in parser.tags:
        style = attrs.get("style", "")
        fg = re.search(r"(?:^|;)\s*color\s*:\s*([^;]+)", style, re.I)
        bg = re.search(r"background-color\s*:\s*([^;]+)", style, re.I)
        if fg and bg:
            ratio = contrast_ratio(fg.group(1), bg.group(1))
            if ratio is not None and ratio < 4.5:
                findings.append(Finding("COLOR_CONTRAST", "High", "Text contrast is below the WCAG AA target", f"<{tag}> contrast ratio: {ratio:.2f}:1", "Low contrast makes text difficult to read, especially for people with low vision.", True))
    return findings, parser


def standards_analyst_agent(findings: list[Finding], parser: PageParser) -> list[Finding]:
    """Agent 2: attach the applicable WCAG success criterion and rationale."""
    mapping = {
        "IMG_ALT": ("WCAG 2.2 — 1.1.1 Non-text Content", "Use meaningful alt text; use alt=\"\" only for decorative images."),
        "FORM_LABEL": ("WCAG 2.2 — 1.3.1 Info and Relationships / 3.3.2 Labels or Instructions", "Associate every control with a visible <label for=...> or an appropriate accessible name."),
        "PAGE_LANG": ("WCAG 2.2 — 3.1.1 Language of Page", "Set the primary language, e.g. <html lang=\"en\">."),
        "PAGE_TITLE": ("WCAG 2.2 — 2.4.2 Page Titled", "Provide a concise, unique <title> that describes the page purpose."),
        "COLOR_CONTRAST": ("WCAG 2.2 — 1.4.3 Contrast (Minimum)", "Normal text should generally reach at least 4.5:1; large text has a 3:1 threshold."),
    }
    for item in findings:
        standard, recommendation = mapping[item.rule_id]
        item.why_it_matters = f"{standard}. {item.why_it_matters}"
        item.recommendation = recommendation
    return findings


def fix_recommendation_agent(findings: list[Finding]) -> list[Finding]:
    """Agent 3: generate implementation-focused, reviewable fix guidance."""
    snippets = {
        "IMG_ALT": 'Example: <img src="team.jpg" alt="Support team answering customer calls">',
        "FORM_LABEL": 'Example: <label for="email">Email address</label><input id="email" name="email" type="email">',
        "PAGE_LANG": 'Example: <html lang="en">',
        "PAGE_TITLE": "Example: <title>Contact support | AccessAble AI</title>",
        "COLOR_CONTRAST": "Try a darker foreground or lighter background, then retest the final rendered styles.",
    }
    for item in findings:
        item.recommendation += " " + snippets[item.rule_id]
    return findings


def validation_agent(findings: list[Finding]) -> tuple[list[Finding], list[str]]:
    """Agent 4: distinguish reliable automation from required human evaluation."""
    for item in findings:
        if item.rule_id == "COLOR_CONTRAST":
            item.validation = "Automated calculation passed on supplied inline colours; confirm all states, images, gradients and inherited CSS in a browser."
        else:
            item.validation = "Automated DOM check completed; a human must still verify that the content and wording are appropriate."
    human_checks = [
        "Is every image description meaningful in its context (not merely present)?",
        "Can all functionality be completed with a keyboard, including focus order and visible focus?",
        "Does a screen-reader journey make sense for headings, landmarks, errors and dynamic updates?",
        "Are instructions, timing, motion and cognitive load suitable for real users?",
    ]
    return findings, human_checks


def critic_agent(findings: list[Finding]) -> list[str]:
    """Agent 5: verify hand-off completeness before the UI receives output."""
    review_notes: list[str] = []
    for item in findings:
        missing = [field for field in ("why_it_matters", "recommendation", "validation") if not getattr(item, field)]
        if missing:
            review_notes.append(f"{item.rule_id} is missing: {', '.join(missing)}.")
    if not review_notes:
        review_notes.append("Critic check passed: each finding contains standards context, a recommendation, and validation guidance.")
    return review_notes


def findings_to_rows(findings: list[Finding]) -> list[dict[str, Any]]:
    """Return the stable, CSV-ready representation consumed by the UI."""
    return [finding.to_dict() for finding in findings]


def run_audit(html: str) -> dict[str, Any]:
    plan = planner_agent(html)
    if plan["status"] != "ready":
        return {
            "status": plan["status"], "message": plan["message"], "plan": plan,
            "findings": [], "counts": {"High": 0, "Medium": 0, "Low": 0},
            "human_checks": [], "critic_notes": [],
        }
    try:
        scanned, parser = scanner_agent(html)
    except Exception as exc:  # Defensive UI boundary for malformed/unexpected input.
        return {
            "status": "error", "message": f"The audit could not parse this input: {exc}", "plan": plan,
            "findings": [], "counts": {"High": 0, "Medium": 0, "Low": 0},
            "human_checks": [], "critic_notes": [],
        }
    analysed = standards_analyst_agent(scanned, parser)
    recommended = fix_recommendation_agent(analysed)
    validated, human_checks = validation_agent(recommended)
    counts = {level: sum(item.severity == level for item in validated) for level in ("High", "Medium", "Low")}
    return {
        "status": "complete", "message": "Audit complete.", "plan": plan, "findings": validated,
        "counts": counts, "human_checks": human_checks, "critic_notes": critic_agent(validated),
    }
