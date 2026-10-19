# AccessAble AI

> CA-3 submission | Priyansh Pandey | Agentic AI Proof of Concept

AccessAble AI is a Streamlit proof of concept for web development and QA teams. It evaluates supplied HTML for a selected set of accessibility barriers, explains the relevant WCAG 2.2 context, recommends fixes, and makes the human-review boundary explicit.

## Problem and solution

Small teams can publish basic accessibility barriers without catching them during routine implementation. The PoC turns a single HTML review into a structured workflow: **Planner → Scanner → Standards Analyst → Fix Recommendation → Validation Agent → Critic**. Each stage receives structured output from the previous stage; no stage claims capabilities that the code does not implement.

## Features

- Synthetic broken and improved store-page demos, plus pasted custom HTML
- Five deterministic checks: image alt text, form labels, document language, page title, and limited inline contrast
- Severity counts, evidence, WCAG 2.2 context, fix examples, validation guidance, and CSV export
- Planner and critic hand-offs made visible in the UI
- A human-review checklist that prevents a false claim of full conformance

## Architecture

See [architecture.md](architecture.md) for the full data flow and agent hand-off contracts.

## Run locally

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

Use **Broken store page** for the presentation demo, then switch to **Improved store page** to show the reduction in automated findings. Empty input receives a safe prompt and malformed HTML is handled without crashing the audit.

Run the checks with:

```powershell
python -m unittest discover -s tests -v
```

## What the PoC checks

| Rule | Example barrier | Automation |
|---|---|---|
| `IMG_ALT` | Missing image alternative | Yes (presence only) |
| `FORM_LABEL` | Form field without accessible name | Yes |
| `COLOR_CONTRAST` | Inline foreground/background contrast below 4.5:1 | Yes, limited scope |
| `PAGE_LANG` | Missing document language | Yes |
| `PAGE_TITLE` | Missing page title | Yes |

## Limitation

Automated tools cannot determine whether alt text is meaningful, keyboard interaction works, focus is logical, or a screen-reader journey makes sense. The validation agent explicitly produces a human-review checklist rather than claiming compliance.

## CA-3 deliverables

- [Final presentation](deliverables/AccessAble_AI_CA3_Presentation.pptx)
- [Final report](deliverables/AccessAble_AI_CA3_Final_Report.docx)
- [Five-minute speaking script](deliverables/five_minute_speaking_script.md)
- [Supporting technical documentation](docs/project_documentation.md)

## Repository structure

```text
app.py                  Streamlit user interface
audit_engine.py         Deterministic agent workflow and rule logic
sample_pages.py         Synthetic demonstration pages
architecture.md         Architecture and hand-off contracts
tests/                  Automated unittest suite
docs/                   Supporting project documentation
deliverables/           Final CA-3 PPTX, DOCX and speaking script
assets/                 Architecture/supporting visual assets
```
