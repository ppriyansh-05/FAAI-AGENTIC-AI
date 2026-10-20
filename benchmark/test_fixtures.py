"""Comprehensive Synthetic Test Fixtures for AccessAble AI Benchmark.

Each fixture is carefully labelled with ground-truth expected violations and rationale.
"""
from __future__ import annotations

FIXTURES: list[dict] = [
    {
        "id": "fixture_01_missing_alt",
        "category": "classic_barrier",
        "description": "Image completely missing alt attribute",
        "html": '<!doctype html><html lang="en"><head><title>Test</title></head><body><img src="avatar.png"></body></html>',
        "expected_violations": {"IMG_ALT"},
    },
    {
        "id": "fixture_02_decorative_alt_legitimate",
        "category": "edge_case_pass",
        "description": "Decorative image with empty alt attribute (WCAG Technique H67)",
        "html": '<!doctype html><html lang="en"><head><title>Test</title></head><body><img src="divider.png" alt=""></body></html>',
        "expected_violations": set(),  # Must NOT report IMG_ALT!
    },
    {
        "id": "fixture_03_aria_hidden_img",
        "category": "edge_case_pass",
        "description": "Image marked aria-hidden='true' or role='presentation'",
        "html": '<!doctype html><html lang="en"><head><title>Test</title></head><body><img src="icon.svg" aria-hidden="true"><img src="bg.png" role="presentation"></body></html>',
        "expected_violations": set(),
    },
    {
        "id": "fixture_04_missing_form_label",
        "category": "classic_barrier",
        "description": "Input field with no label, aria-label, or title",
        "html": '<!doctype html><html lang="en"><head><title>Test</title></head><body><form><input id="username" type="text"></form></body></html>',
        "expected_violations": {"FORM_LABEL"},
    },
    {
        "id": "fixture_05_wrapping_label_pass",
        "category": "edge_case_pass",
        "description": "Input control properly wrapped inside <label>",
        "html": '<!doctype html><html lang="en"><head><title>Test</title></head><body><form><label>Search query: <input type="text"></label></form></body></html>',
        "expected_violations": set(),
    },
    {
        "id": "fixture_06_aria_label_pass",
        "category": "edge_case_pass",
        "description": "Input control with programmatic aria-label",
        "html": '<!doctype html><html lang="en"><head><title>Test</title></head><body><form><input type="text" aria-label="Search items"></form></body></html>',
        "expected_violations": set(),
    },
    {
        "id": "fixture_07_missing_lang",
        "category": "classic_barrier",
        "description": "HTML tag missing lang attribute",
        "html": '<html><head><title>Test</title></head><body><p>Hello world</p></body></html>',
        "expected_violations": {"PAGE_LANG"},
    },
    {
        "id": "fixture_08_empty_lang",
        "category": "edge_case_barrier",
        "description": "HTML tag with empty or whitespace lang attribute",
        "html": '<html lang="  "><head><title>Test</title></head><body><p>Hello world</p></body></html>',
        "expected_violations": {"PAGE_LANG"},
    },
    {
        "id": "fixture_09_missing_title",
        "category": "classic_barrier",
        "description": "Document missing head title",
        "html": '<!doctype html><html lang="en"><head></head><body><h1>Main</h1></body></html>',
        "expected_violations": {"PAGE_TITLE"},
    },
    {
        "id": "fixture_10_poor_contrast_hex",
        "category": "classic_barrier",
        "description": "Grey text on white background failing 4.5:1 ratio",
        "html": '<!doctype html><html lang="en"><head><title>Test</title></head><body><p style="color: #999999; background-color: #ffffff">Faint text</p></body></html>',
        "expected_violations": {"COLOR_CONTRAST"},
    },
    {
        "id": "fixture_11_large_text_contrast_pass",
        "category": "edge_case_pass",
        "description": "Large text with 3.2:1 contrast passing WCAG large text threshold (3.0:1)",
        "html": '<!doctype html><html lang="en"><head><title>Test</title></head><body><h1 style="color: #667788; background-color: #ffffff; font-size: 26px;">Big banner text</h1></body></html>',
        "expected_violations": set(),
    },
    {
        "id": "fixture_12_skipped_heading",
        "category": "heading_hierarchy",
        "description": "Heading level jumping directly from h1 to h4",
        "html": '<!doctype html><html lang="en"><head><title>Test</title></head><body><h1>Top</h1><h4>Sub Section</h4></body></html>',
        "expected_violations": {"HEADING_ORDER"},
    },
    {
        "id": "fixture_13_empty_link",
        "category": "link_discernible",
        "description": "Anchor element with no text, image, or aria-label",
        "html": '<!doctype html><html lang="en"><head><title>Test</title></head><body><a href="/profile"></a></body></html>',
        "expected_violations": {"LINK_DISCERNIBLE"},
    },
    {
        "id": "fixture_14_fully_accessible_page",
        "category": "gold_standard_pass",
        "description": "Exemplary accessible page adhering to all automated checks",
        "html": '''<!doctype html>
<html lang="en">
<head>
  <title>Accessible Customer Portal | Home</title>
</head>
<body>
  <header>
    <h1>Customer Portal</h1>
  </header>
  <main>
    <h2>Account Overview</h2>
    <img src="chart.png" alt="Monthly usage graph showing 20% savings">
    <p style="color: #111827; background-color: #ffffff">Welcome back! Check your latest statements below.</p>
    <form>
      <label for="query">Search records</label>
      <input id="query" name="query" type="text">
      <button type="submit">Submit</button>
    </form>
    <a href="/help">Need help? Read our accessibility guide</a>
  </main>
</body>
</html>''',
        "expected_violations": set(),
    },
    {
        "id": "fixture_15_malformed_html_robustness",
        "category": "malformed_robustness",
        "description": "Unclosed tags and unusual casing must not crash scanner",
        "html": '<HTML LANG="en"><HEAD><TITLE>OK</TITLE><BODY><P style="color: #111; background-color: #fff">Text<IMG SRC="sample.jpg"><INPUT TYPE="text" ID="test"><LABEL FOR="test">Test</LABEL>',
        "expected_violations": {"IMG_ALT"},
    },
]
