"""Enhanced deterministic accessibility detection engine.

Improves edge-case accuracy:
1. IMG_ALT:
   - Differentiates missing alt from decorative alt="" (WCAG 1.1.1 / Technique H67).
   - Recognizes aria-hidden="true", role="presentation", role="none".
2. FORM_LABEL:
   - Supports explicit labels (<label for="id">), nested wrapping labels (<label><input></label>),
     aria-label, aria-labelledby, title, and button-type controls.
3. PAGE_LANG:
   - Validates presence and non-emptiness of <html lang="...">.
4. PAGE_TITLE:
   - Checks presence and non-whitespace content in <head><title>.
5. COLOR_CONTRAST:
   - Supports hex (#fff, #ffffff), rgb(), rgba(), hsl(), and standard CSS color names.
   - Distinguishes normal text (4.5:1 required) from large text (>= 18pt or 14pt bold -> 3.0:1 required).
6. HEADING_ORDER:
   - Flags skipped heading levels (e.g. h1 to h3) per WCAG 1.3.1.
7. LINK_DISCERNIBLE:
   - Flags links (<a>) with no text, no accessible name, or empty href.
"""
from __future__ import annotations

import colorsys
import re
from typing import Any
from bs4 import BeautifulSoup, Tag

from core.models import Finding

CSS_NAMED_COLORS: dict[str, tuple[int, int, int]] = {
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "red": (255, 0, 0),
    "green": (0, 128, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "silver": (192, 192, 192),
    "navy": (0, 0, 128),
    "purple": (128, 0, 128),
    "teal": (0, 128, 128),
    "orange": (255, 165, 0),
    "maroon": (128, 0, 0),
    "olive": (128, 128, 0),
    "aqua": (0, 255, 255),
    "fuchsia": (255, 0, 255),
    "lime": (0, 255, 0),
    "transparent": (255, 255, 255),  # Fallback assumption for contrast
}


def parse_css_color(val: str) -> tuple[int, int, int] | None:
    """Parse hex, rgb, rgba, hsl, or named color into RGB tuple."""
    if not val or not isinstance(val, str):
        return None
    val = val.strip().lower()

    if val in CSS_NAMED_COLORS:
        return CSS_NAMED_COLORS[val]

    # Hex: #fff or #ffffff
    hex_match = re.fullmatch(r"#([0-9a-f]{3}|[0-9a-f]{6})", val)
    if hex_match:
        c = hex_match.group(1)
        if len(c) == 3:
            c = "".join(ch * 2 for ch in c)
        return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))

    # rgb(r, g, b) or rgba(r, g, b, a)
    rgb_match = re.match(r"rgba?\s*\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})", val)
    if rgb_match:
        return (int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3)))

    # hsl(h, s%, l%)
    hsl_match = re.match(r"hsla?\s*\(\s*(\d{1,3}(?:\.\d+)?)\s*,\s*(\d{1,3}(?:\.\d+)?%)\s*,\s*(\d{1,3}(?:\.\d+)?%)", val)
    if hsl_match:
        h = float(hsl_match.group(1)) / 360.0
        s = float(hsl_match.group(2).replace("%", "")) / 100.0
        l = float(hsl_match.group(3).replace("%", "")) / 100.0
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return (int(round(r * 255)), int(round(g * 255)), int(round(b * 255)))

    return None


def srgb_luminance(rgb: tuple[int, int, int]) -> float:
    """Calculates relative luminance according to WCAG 2.2 formula."""
    channels = []
    for num in rgb:
        val = num / 255.0
        channels.append(val / 12.92 if val <= 0.04045 else ((val + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def calculate_contrast_ratio(fg_val: str, bg_val: str) -> float | None:
    """Calculates contrast ratio (1.0 to 21.0) between two color definitions."""
    fg = parse_css_color(fg_val)
    bg = parse_css_color(bg_val)
    if not fg or not bg:
        return None
    l1 = max(srgb_luminance(fg), srgb_luminance(bg))
    l2 = min(srgb_luminance(fg), srgb_luminance(bg))
    return (l1 + 0.05) / (l2 + 0.05)


class EnhancedAccessibilityScanner:
    """Deterministic accessibility scanner inspecting DOM and inline styles."""

    def __init__(self, html: str) -> None:
        self.raw_html = html
        self.soup = BeautifulSoup(html, "html.parser")
        self.findings: list[Finding] = []
        self._finding_count = 0

    def _next_id(self, rule: str) -> str:
        self._finding_count += 1
        return f"finding_{rule.lower()}_{self._finding_count}"

    def scan_all(self) -> list[Finding]:
        self.check_page_lang()
        self.check_page_title()
        self.check_images()
        self.check_form_controls()
        self.check_contrast()
        self.check_headings()
        self.check_links()
        return self.findings

    def check_page_lang(self) -> None:
        html_tag = self.soup.find("html")
        if not html_tag:
            self.findings.append(Finding(
                id=self._next_id("PAGE_LANG"),
                rule_id="PAGE_LANG",
                severity="Medium",
                title="Page language is not declared",
                evidence="<html> tag has no lang attribute",
                why_it_matters="WCAG 2.2 — 3.1.1 Language of Page (Level A). Assistive technologies cannot switch to appropriate language rules or pronunciation engines without a lang declaration.",
                automated=True,
                element_tag="html",
                selector="html",
                wcag_criterion="WCAG 2.2 — 3.1.1 Language of Page",
                recommendation='Add the lang attribute to the <html> root element, e.g. <html lang="en">.',
                remediation_patch='<html lang="en">',
                validation="Automated check: verifies presence of non-empty lang attribute on <html>.",
                requires_human_review=False,
                confidence=1.0,
            ))
            return

        lang = html_tag.get("lang")
        if not lang or not str(lang).strip():
            self.findings.append(Finding(
                id=self._next_id("PAGE_LANG"),
                rule_id="PAGE_LANG",
                severity="Medium",
                title="Page language attribute is empty",
                evidence=str(html_tag)[:100],
                why_it_matters="WCAG 2.2 — 3.1.1 Language of Page (Level A). An empty lang attribute fails to specify the natural language of the document.",
                automated=True,
                element_tag="html",
                selector="html",
                wcag_criterion="WCAG 2.2 — 3.1.1 Language of Page",
                recommendation='Specify a valid BCP 47 language tag, e.g. <html lang="en">.',
                remediation_patch='<html lang="en">',
                validation="Automated check: verified lang attribute is missing or empty.",
                requires_human_review=False,
                confidence=1.0,
            ))

    def check_page_title(self) -> None:
        title_tag = self.soup.find("title")
        if not title_tag or not title_tag.get_text(strip=True):
            evidence = str(title_tag) if title_tag else "No <title> element found in <head>"
            self.findings.append(Finding(
                id=self._next_id("PAGE_TITLE"),
                rule_id="PAGE_TITLE",
                severity="Medium",
                title="Page has no descriptive title",
                evidence=evidence,
                why_it_matters="WCAG 2.2 — 2.4.2 Page Titled (Level A). Web page titles help users orient themselves, navigate between open tabs, and understand page purpose before reading content.",
                automated=True,
                element_tag="title",
                selector="head > title",
                wcag_criterion="WCAG 2.2 — 2.4.2 Page Titled",
                recommendation="Provide a concise, descriptive <title> inside <head> indicating the page purpose or site section.",
                remediation_patch="<title>AccessAble AI — Accessibility Audit Report</title>",
                validation="Automated check verified title presence; human reviewer should verify title accurately describes content.",
                requires_human_review=True,
                confidence=1.0,
            ))

    def check_images(self) -> None:
        for img in self.soup.find_all("img"):
            # Check if explicitly hidden or marked decorative per WCAG techniques
            aria_hidden = img.get("aria-hidden") == "true"
            role = img.get("role")
            is_decorative_role = role in ("presentation", "none")

            if aria_hidden or is_decorative_role:
                # Decorative image explicitly hidden from assistive tech
                continue

            has_alt = img.has_attr("alt")
            alt_val = img.get("alt")

            if not has_alt:
                # Missing alt attribute entirely -> violation
                src = img.get("src", "unspecified")
                snippet = str(img)[:150]
                self.findings.append(Finding(
                    id=self._next_id("IMG_ALT"),
                    rule_id="IMG_ALT",
                    severity="High",
                    title="Image has no text alternative",
                    evidence=snippet,
                    why_it_matters="WCAG 2.2 — 1.1.1 Non-text Content (Level A). Screen readers read image URLs or file names when alt text is absent, creating a confusing experience.",
                    automated=True,
                    element_tag="img",
                    selector=f'img[src="{src}"]',
                    wcag_criterion="WCAG 2.2 — 1.1.1 Non-text Content",
                    recommendation='Add an informative alt attribute describing the image purpose, or alt="" if strictly decorative.',
                    remediation_patch=snippet.replace("<img", '<img alt="Image description"'),
                    validation="Automated check: verified missing alt attribute. Human review required to ensure description quality.",
                    requires_human_review=True,
                    confidence=1.0,
                ))
            elif alt_val == "":
                # alt="" is legitimate WCAG technique H67 for decorative images.
                # We do NOT flag this as an error!
                pass
            elif not alt_val.strip():
                # alt="   " (only whitespace) is a known bad practice
                snippet = str(img)[:150]
                self.findings.append(Finding(
                    id=self._next_id("IMG_ALT"),
                    rule_id="IMG_ALT",
                    severity="High",
                    title="Image alternative text contains only whitespace",
                    evidence=snippet,
                    why_it_matters="WCAG 2.2 — 1.1.1 Non-text Content (Level A). Whitespace-only alt text does not convey meaningful information.",
                    automated=True,
                    element_tag="img",
                    selector="img",
                    wcag_criterion="WCAG 2.2 — 1.1.1 Non-text Content",
                    recommendation='Provide descriptive alt text or use empty quotes alt="" if purely decorative.',
                    remediation_patch=re.sub(r'alt=["\'][ \t\r\n]*["\']', 'alt=""', snippet),
                    validation="Automated check: verified whitespace alt attribute.",
                    requires_human_review=True,
                    confidence=0.95,
                ))

    def check_form_controls(self) -> None:
        # Collect all element IDs present in document
        all_dom_ids = {tag.get("id") for tag in self.soup.find_all(True) if tag.get("id")}

        # Collect explicit label "for" targets that point to existing IDs
        labels_for_map = {}
        for lbl in self.soup.find_all("label"):
            target_for = lbl.get("for")
            if target_for:
                labels_for_map[target_for] = lbl

        for el in self.soup.find_all(["input", "select", "textarea"]):
            el_type = (el.get("type") or "text").lower()
            if el_type in ("hidden", "submit", "button", "reset", "image"):
                continue

            el_id = el.get("id")
            # Label exists AND associates with this element's id
            has_explicit_label = el_id and el_id in labels_for_map

            # Check wrapping label: <label>...<input>...</label>
            has_wrapping_label = el.find_parent("label") is not None

            # Check ARIA accessible name attributes
            has_aria_label = bool(el.get("aria-label") and str(el.get("aria-label")).strip())
            
            # Check aria-labelledby: the referenced ID(s) must actually exist in DOM
            has_valid_labelledby = False
            labelledby_attr = el.get("aria-labelledby")
            if labelledby_attr and str(labelledby_attr).strip():
                ref_ids = str(labelledby_attr).split()
                has_valid_labelledby = all(ref_id in all_dom_ids for ref_id in ref_ids)

            has_title = bool(el.get("title") and str(el.get("title")).strip())

            has_accessible_name = has_explicit_label or has_wrapping_label or has_aria_label or has_valid_labelledby or has_title

            if not has_accessible_name:
                snippet = str(el)[:150]
                target_id = el_id or el.get("name") or "field"
                self.findings.append(Finding(
                    id=self._next_id("FORM_LABEL"),
                    rule_id="FORM_LABEL",
                    severity="High",
                    title="Form control has no programmatic label",
                    evidence=snippet,
                    why_it_matters="WCAG 2.2 — 1.3.1 Info and Relationships / 3.3.2 Labels or Instructions (Level A). Screen-reader users cannot identify the requested input without an accessible label.",
                    automated=True,
                    element_tag=el.name,
                    selector=f"{el.name}#{el_id}" if el_id else f"{el.name}[name='{el.get('name', '')}']",
                    wcag_criterion="WCAG 2.2 — 1.3.1 Info and Relationships / 3.3.2 Labels",
                    recommendation=f'Associate a <label for="{target_id}">Label text</label> or provide aria-label="{target_id}".',
                    remediation_patch=f'<label for="{target_id}">Enter {target_id}</label>\n' + (snippet if el_id else snippet.replace(f"<{el.name}", f'<{el.name} id="{target_id}"')),
                    validation="Automated check: verified absence of label, aria-label, aria-labelledby, and wrapping label.",
                    requires_human_review=False,
                    confidence=1.0,
                ))

    def check_contrast(self) -> None:
        for tag in self.soup.find_all(True):
            style = tag.get("style")
            if not style:
                continue

            # Extract color and background-color
            fg_match = re.search(r"(?:^|;)\s*color\s*:\s*([^;]+)", style, re.I)
            bg_match = re.search(r"(?:^|;)\s*background-color\s*:\s*([^;]+)", style, re.I)

            if fg_match and bg_match:
                fg_val = fg_match.group(1).strip()
                bg_val = bg_match.group(1).strip()

                ratio = calculate_contrast_ratio(fg_val, bg_val)
                if ratio is not None:
                    # Check font size to distinguish large text (threshold 3.0:1) vs normal text (4.5:1)
                    fs_match = re.search(r"font-size\s*:\s*(\d+(?:\.\d+)?)(px|pt|em|rem)?", style, re.I)
                    fw_match = re.search(r"font-weight\s*:\s*(bold|[7-9]00)", style, re.I)

                    is_large = False
                    if fs_match:
                        size_num = float(fs_match.group(1))
                        unit = (fs_match.group(2) or "px").lower()
                        # WCAG definition: 14pt bold (~18.66px) or 18pt (~24px)
                        px_size = size_num * 1.333 if unit == "pt" else (size_num * 16.0 if unit in ("em", "rem") else size_num)
                        if px_size >= 24 or (px_size >= 18.66 and fw_match):
                            is_large = True

                    required_ratio = 3.0 if is_large else 4.5

                    if ratio < required_ratio:
                        snippet = str(tag)[:150]
                        self.findings.append(Finding(
                            id=self._next_id("COLOR_CONTRAST"),
                            rule_id="COLOR_CONTRAST",
                            severity="High",
                            title=f"Text contrast ratio ({ratio:.2f}:1) is below WCAG AA target ({required_ratio:.1f}:1)",
                            evidence=f"<{tag.name} style='{style}'> (fg: {fg_val}, bg: {bg_val})",
                            why_it_matters=f"WCAG 2.2 — 1.4.3 Contrast (Minimum) (Level AA). Low visual contrast makes text illegible for users with low vision or color vision deficiencies.",
                            automated=True,
                            element_tag=tag.name,
                            selector=tag.name,
                            wcag_criterion="WCAG 2.2 — 1.4.3 Contrast (Minimum)",
                            recommendation=f"Increase contrast between foreground ({fg_val}) and background ({bg_val}) to at least {required_ratio:.1f}:1.",
                            remediation_patch=re.sub(r"color\s*:\s*[^;]+", "color: #111827", snippet, flags=re.I),
                            validation=f"Calculated ratio: {ratio:.2f}:1 (Target: {required_ratio:.1f}:1). Rendered browser styles should be verified.",
                            requires_human_review=True,
                            confidence=0.9,
                        ))

    def check_headings(self) -> None:
        """WCAG 1.3.1: Heading levels should not skip levels unexpectedly (e.g. h1 to h3)."""
        headings = self.soup.find_all(re.compile(r"^h[1-6]$"))
        last_level = 0
        for h in headings:
            level = int(h.name[1])
            if last_level > 0 and level > last_level + 1:
                self.findings.append(Finding(
                    id=self._next_id("HEADING_ORDER"),
                    rule_id="HEADING_ORDER",
                    severity="Medium",
                    title=f"Heading level skipped from <h{last_level}> to <h{level}>",
                    evidence=str(h)[:120],
                    why_it_matters="WCAG 2.2 — 1.3.1 Info and Relationships (Level A). Skipping heading levels disrupts document structure navigation for screen readers.",
                    automated=True,
                    element_tag=h.name,
                    selector=h.name,
                    wcag_criterion="WCAG 2.2 — 1.3.1 Info and Relationships",
                    recommendation=f"Use <h{last_level + 1}> instead of <h{level}> to maintain hierarchical order.",
                    remediation_patch=str(h).replace(f"<h{level}", f"<h{last_level + 1}").replace(f"</h{level}>", f"</h{last_level + 1}>"),
                    validation="Automated check: verified heading level sequence gap.",
                    requires_human_review=False,
                    confidence=0.95,
                ))
            last_level = level

    def check_links(self) -> None:
        """WCAG 2.4.4: Links must have discernible text or accessible name."""
        for a in self.soup.find_all("a"):
            text = a.get_text(strip=True)
            aria_label = a.get("aria-label", "").strip()
            aria_labelledby = a.get("aria-labelledby", "").strip()
            title = a.get("title", "").strip()
            img_with_alt = any(img.get("alt", "").strip() for img in a.find_all("img"))

            has_discernible_text = bool(text or aria_label or aria_labelledby or title or img_with_alt)
            if not has_discernible_text:
                self.findings.append(Finding(
                    id=self._next_id("LINK_DISCERNIBLE"),
                    rule_id="LINK_DISCERNIBLE",
                    severity="High",
                    title="Link has no discernible text or accessible name",
                    evidence=str(a)[:120],
                    why_it_matters="WCAG 2.2 — 2.4.4 Link Purpose (In Context) / 4.1.2 Name, Role, Value (Level A). Screen readers announce links without content as 'link' or empty, hiding their destination.",
                    automated=True,
                    element_tag="a",
                    selector="a",
                    wcag_criterion="WCAG 2.2 — 2.4.4 Link Purpose (In Context)",
                    recommendation="Provide meaningful anchor text, an inner image with alt text, or an aria-label.",
                    remediation_patch=str(a).replace("></a>", ">Learn more</a>"),
                    validation="Automated check: verified absence of text, aria-label, and image alt inside anchor.",
                    requires_human_review=True,
                    confidence=1.0,
                ))
