# AccessAble AI — Multi-Agent Website Accessibility Auditor

[![AccessAble AI CI](https://github.com/ppriyansh-05/FAAI-AGENTIC-AI/actions/workflows/ci.yml/badge.svg)](https://github.com/ppriyansh-05/FAAI-AGENTIC-AI/actions/workflows/ci.yml)
> **Autonomous Multi-Agent Accessibility Auditing & Safe Remediation Sandbox**  
> Evaluates web pages against W3C WCAG 2.2 standards, synthesizes contextual fixes, and verifies resolution in an isolated retest sandbox.

---

## 🌟 Key Highlights

- **Multi-Engine Auditing**: High-precision deterministic Python DOM parser + headless Playwright with industry-standard `axe-core`.
- **True Agentic State Machine**: Features dynamic planning, signal harmonizing, remediation synthesis, and **Critic-driven retry loops** with bounded iterations (`max_retries=3`).
- **Safe Fix-and-Retest Sandbox**: Candidate code fixes are applied to an isolated in-memory buffer and re-scanned. Generates unified before/after diffs (`difflib.unified_diff`) to prove zero regressions.
- **Enterprise-Grade SSRF Protection**: Public URL scanning strictly blocks private IP subnets (`10.0.0.0/8`, `192.168.0.0/16`, `172.16.0.0/12`), loopbacks (`127.0.0.1`, `::1`), and cloud metadata APIs (`169.254.169.254`).
- **Quantitative Benchmark Evaluator**: Evaluated on 15 synthetic ground-truth test fixtures measuring Precision, Recall, F1-Score, and automated fix success rates.
- **Human-in-the-Loop Boundaries**: Explicitly rejects false claims of 100% automated conformance; surfaces mandatory human checklists for assistive technologies (screen readers, keyboard traps).

---

## 📐 Architecture & Agent Team

```
Input (HTML/URL) ──> [Agent 0: Planner] ──> [Agent 1: Scanner (DOM / Axe)]
                                                   │
[Agent 4: Critic Retest Sandbox] <── [Agent 3: Remediation] <── [Agent 2: WCAG Standards Analyst]
        │
        ├── (Regression / Retry) ──> Loops back to Remediation Agent (Max 3 retries)
        └── (Verified Clean)    ──> [Agent 5: Validation Boundary] ──> Unified Diff & Reports
```

For complete state transitions and agent hand-off specifications, see [architecture.md](architecture.md).

---

## 📊 Benchmark Evaluation Results

Evaluated across 15 synthetic, ground-truth labeled fixtures:

| Metric | Measured Score | Evaluation Notes |
|---|---|---|
| **Precision** | **100.00%** | Zero false positives on decorative `alt=""` and nested form labels |
| **Recall** | **100.00%** | Accurately flagged all classic accessibility barriers |
| **F1-Score** | **1.0000** | Harmonic mean of precision and recall |
| **Fix Retest Pass Rate**| **55.56%** | Automated patches verified clean; complex barriers flagged for human review |
| **Execution Time** | **< 0.05s** | High-performance deterministic evaluation |

---

## 🚀 Quickstart & Local Setup

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/ppriyansh-05/FAAI-AGENTIC-AI.git
cd FAAI-AGENTIC-AI
python -m pip install -r requirements.txt
python -m playwright install chromium
```

### 2. Run the Streamlit Application
```bash
streamlit run app.py
```

### 3. Run Automated Tests & Benchmark
```bash
# Run unit and integration tests
python -m unittest discover -s tests -v

# Run the quantitative benchmark evaluator
python -m benchmark.evaluator
```

---

## 🛡️ WCAG 2.2 Supported Rules

- **`IMG_ALT`**: WCAG 1.1.1 Non-text Content (Distinguishes missing alt from decorative `alt=""` per Technique H67).
- **`FORM_LABEL`**: WCAG 1.3.1 / 3.3.2 Labels or Instructions (Supports wrapping labels, `aria-label`, `aria-labelledby`, and `title`).
- **`COLOR_CONTRAST`**: WCAG 1.4.3 Contrast Minimum (Differentiates 4.5:1 normal text from 3.0:1 large text; supports hex, rgb, hsl).
- **`PAGE_LANG`**: WCAG 3.1.1 Language of Page.
- **`PAGE_TITLE`**: WCAG 2.4.2 Page Titled.
- **`HEADING_ORDER`**: WCAG 1.3.1 Info and Relationships (Catches skipped levels like `h1` to `h3`).
- **`LINK_DISCERNIBLE`**: WCAG 2.4.4 Link Purpose (In Context).

---

## 📁 Deliverables & Repository Structure

```text
├── app.py                      # Modern multi-tab Streamlit interface
├── audit_engine.py             # Backward-compatible API bridge
├── sample_pages.py             # Synthetic test pages
├── architecture.md             # Architecture diagram & hand-off contracts
├── core/
│   ├── models.py               # Finding, RemediationResult, AuditState schemas
│   ├── scanner.py              # Enhanced deterministic DOM scanner
│   ├── browser_scanner.py      # Playwright + axe-core browser runner
│   ├── remediation.py          # Safe sandbox fix-and-retest engine & diffs
│   ├── orchestrator.py         # Agentic state machine orchestrator
│   └── security.py             # SSRF firewall & IP validator
├── benchmark/
│   ├── test_fixtures.py        # 15 ground-truth labeled fixtures
│   └── evaluator.py            # Quantitative benchmark engine
├── tests/
│   ├── test_audit_engine.py    # CA-3 regression test suite
│   └── test_enhanced_engine.py # New rules, security, and agent tests
├── deliverables/               # Preserved CA-3 presentation, report, script
└── docs/
    └── IMPLEMENTATION_ROADMAP.md # Engineering audit and roadmap
```
