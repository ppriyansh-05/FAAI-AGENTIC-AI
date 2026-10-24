# AccessAble AI — Multi-Agent Website Accessibility Auditor

A multi-agent accessibility auditing prototype for common WCAG 2.2 barriers. The UI is built with NiceGUI using a dark glassmorphism design; the existing audit engine remains in the core modules.

## UI migration

- Replaced the Streamlit UI with NiceGUI.
- Preserved the existing audit_engine.run_audit interface, scanner/orchestrator, remediation sandbox, benchmark evaluator, and SQLite audit history.
- Added responsive glass panels, severity cards, findings, agent trace, benchmark table, CSV/JSON exports, and history view.
- Gemini configuration uses GEMINI_API_KEY or GOOGLE_API_KEY environment variables.

## Run locally

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install chromium
python app.py
```

Open http://127.0.0.1:8080.

Optional: set GEMINI_API_KEY or GOOGLE_API_KEY in your environment or a local .env file to enable Gemini critic reviews. Do not commit secrets.

## Run tests

```bash
python -m unittest discover -s tests -v
python -m benchmark.evaluator
```

## Render deployment

The included render.yaml runs python app.py. Configure GEMINI_API_KEY or GOOGLE_API_KEY in Render environment settings if required. The application binds to Render's PORT environment variable.

## Key styling upgrades

- Deep navy background with violet/cyan gradient accents.
- Translucent glass cards, subtle borders, blur, and soft shadows.
- Inter typography, responsive spacing, compact status pills, and severity colors.
- Responsive workspace with dedicated audit, remediation, benchmark, trace, history, and about views.

## Notes

- Automated results are signals, not certification of WCAG conformance; keyboard, screen-reader, and contextual checks require human validation.
- Public URL scanning retains URL validation in the audit orchestrator.
- Browser scanning requires Playwright/Chromium and may fall back to the existing DOM scanner when unavailable.
