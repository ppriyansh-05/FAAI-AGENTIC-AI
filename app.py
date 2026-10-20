"""AccessAble AI — Multi-Agent Website Accessibility Auditor

Professional, competition-ready Streamlit interface featuring:
- Input sources: Synthetic demo pages, pasted HTML, HTML file upload, secure public URL
- Multi-engine auditing: High-precision deterministic DOM engine & Playwright + Axe-Core
- Genuinely adaptive Critic retry timeline
- Interactive fix-and-retest sandbox with unified diffs and human approval workflow
- Quantitative evaluation benchmark dashboard (18 fixtures)
- Audit history from local SQLite database
- CSV, JSON, and SARIF compliance report export
"""
from __future__ import annotations

import json
import pandas as pd
import streamlit as st

from audit_engine import findings_to_rows, run_audit
from sample_pages import BROKEN_STORE_PAGE, IMPROVED_STORE_PAGE
from benchmark.evaluator import run_benchmark
from core.security import validate_audit_url
from core.database import get_audit_history

st.set_page_config(
    page_title="AccessAble AI — Agentic Accessibility Auditor",
    page_icon="♿",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .badge-high {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-medium {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-low {
        background-color: #E0E7FF;
        color: #3730A3;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">♿ AccessAble AI</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Autonomous Multi-Agent Website Accessibility Auditor & Adaptive Remediation Sandbox</div>', unsafe_allow_html=True)

tab_audit, tab_sandbox, tab_benchmark, tab_trace, tab_history, tab_about = st.tabs([
    "🔍 Audit & Findings",
    "🛠️ Adaptive Remediation Sandbox",
    "📊 Evaluation Benchmark",
    "🤖 Agent Trace & Retries",
    "📜 Audit History",
    "📖 About & Limitations",
])

with st.sidebar:
    st.header("⚙️ Audit Configuration")
    input_mode = st.radio(
        "Choose Input Source",
        ["Synthetic Demo Page", "Paste Raw HTML", "Upload HTML File", "Public URL (Playwright)"],
    )

    use_browser = st.checkbox(
        "Enable Headless Browser (Playwright + Axe-Core)",
        value=False,
        help="Loads rendered DOM and runs industry-standard axe-core rules in an isolated Chromium container.",
    )

    st.markdown("---")
    st.markdown("### 🛡️ Built-in Safeguards")
    st.caption("• Defense-in-depth SSRF protection on public URLs\n• Subresource interception & redirect validation\n• Non-destructive isolated sandbox\n• Genuinely adaptive Critic retries (max 3)\n• Explicit human validation checkpoints")

html_to_audit = ""
target_url = None

if input_mode == "Synthetic Demo Page":
    sample = st.selectbox("Select demo fixture", ["Broken store page", "Improved store page", "Blank template"])
    defaults = {
        "Broken store page": BROKEN_STORE_PAGE,
        "Improved store page": IMPROVED_STORE_PAGE,
        "Blank template": '<!doctype html>\n<html lang="en">\n<head><title>Accessible Demo</title></head>\n<body>\n  <h1>Welcome</h1>\n</body>\n</html>',
    }
    html_to_audit = st.text_area("HTML Content", value=defaults[sample], height=220)

elif input_mode == "Paste Raw HTML":
    html_to_audit = st.text_area("Paste HTML source", height=250, placeholder="<!doctype html>...")

elif input_mode == "Upload HTML File":
    uploaded = st.file_uploader("Upload HTML file", type=["html", "htm"])
    if uploaded:
        html_to_audit = uploaded.read().decode("utf-8", errors="ignore")
        st.success(f"Loaded {uploaded.name} ({len(html_to_audit)} bytes)")

elif input_mode == "Public URL (Playwright)":
    url_input = st.text_input("Enter public website URL (HTTP/HTTPS only)", placeholder="https://example.com")
    if url_input:
        target_url = url_input.strip()
        use_browser = True

# Stale Results Warning
current_fingerprint = f"{input_mode}_{len(html_to_audit)}_{target_url}"
if "last_fingerprint" in st.session_state and st.session_state.last_fingerprint != current_fingerprint and "audit" in st.session_state:
    st.warning("⚠️ Input has changed since the last audit run. Re-run audit to view updated findings.")

if st.button("🚀 Run Multi-Agent Audit", type="primary", use_container_width=True):
    with st.spinner("Multi-agent team active (Planner → Scanner → Standards Analyst → Remediation → Critic)..."):
        try:
            audit_res = run_audit(html_to_audit, use_browser=use_browser, target_url=target_url)
            st.session_state.audit = audit_res
            st.session_state.audited_html = html_to_audit
            st.session_state.last_fingerprint = current_fingerprint
        except Exception as exc:
            st.error(f"Audit failed to execute: {exc}")

# --- TAB 1: AUDIT & FINDINGS ---
with tab_audit:
    if "audit" not in st.session_state:
        st.info("Select an input source on the left sidebar and click **Run Multi-Agent Audit**.")
    else:
        audit = st.session_state.audit
        if audit["status"] == "no_input":
            st.warning(audit["message"])
        elif audit["status"] == "error":
            st.error(audit["message"])
        else:
            findings = audit["findings"]
            counts = audit["counts"]

            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Total Findings", len(findings))
            m2.metric("High Severity", counts.get("High", 0))
            m3.metric("Medium Severity", counts.get("Medium", 0))
            m4.metric("Low Severity", counts.get("Low", 0))
            m5.metric("Engine Mode", audit["plan"].get("engine", "Python DOM"))

            st.markdown("### Findings by Severity")
            if not findings:
                st.success("🎉 No accessibility violations detected by automated checks. Manual verification is still required for assistive technology conformance.")
            else:
                for severity in ["High", "Medium", "Low"]:
                    group = [f for f in findings if f.severity == severity]
                    if group:
                        badge_class = f"badge-{severity.lower()}"
                        st.markdown(f"#### <span class='{badge_class}'>{severity} Priority</span> ({len(group)})", unsafe_allow_html=True)
                        for f in group:
                            with st.expander(f"**{f.rule_id}**: {f.title} (Engine: `{f.engine}`)"):
                                st.markdown(f"**WCAG Criterion**: `{f.wcag_criterion}`")
                                st.markdown(f"**Impact**: {f.why_it_matters}")
                                st.markdown("**Offending Element / Evidence**:")
                                st.code(f.evidence, language="html")
                                st.info(f"**Recommendation**: {f.recommendation}")
                                st.caption(f"**Validation Status**: {f.validation}")

            st.markdown("### 👤 Human Review Checklist (Mandatory for Conformance)")
            for check in audit.get("human_checks", []):
                st.checkbox(check, value=False, key=f"tab1_check_{check}")

            st.markdown("### 📥 Export Audit Report")
            exp_col1, exp_col2, exp_col3 = st.columns(3)
            rows = findings_to_rows(findings)
            if rows:
                df = pd.DataFrame(rows)
                exp_col1.download_button(
                    "Download CSV Report",
                    df.to_csv(index=False),
                    "accessable_ai_report.csv",
                    "text/csv",
                    use_container_width=True,
                )
                exp_col2.download_button(
                    "Download JSON Report",
                    json.dumps(rows, indent=2),
                    "accessable_ai_report.json",
                    "application/json",
                    use_container_width=True,
                )

                # SARIF formatted export
                sarif_report = {
                    "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
                    "version": "2.1.0",
                    "runs": [{
                        "tool": {
                            "driver": {
                                "name": "AccessAble AI",
                                "version": "2.0.0",
                                "rules": [{"id": f.rule_id, "shortDescription": {"text": f.title}} for f in findings]
                            }
                        },
                        "results": [{
                            "ruleId": f.rule_id,
                            "level": "error" if f.severity == "High" else "warning",
                            "message": {"text": f.why_it_matters},
                        } for f in findings]
                    }]
                }
                exp_col3.download_button(
                    "Download SARIF Report",
                    json.dumps(sarif_report, indent=2),
                    "accessable_ai.sarif",
                    "application/json",
                    use_container_width=True,
                )

# --- TAB 2: SAFE REMEDIATION SANDBOX ---
with tab_sandbox:
    st.subheader("🛠️ Adaptive Remediation Sandbox")
    st.markdown("""
    AccessAble AI never modifies live production servers. The **Remediation Agent** proposes targeted context-aware fixes,
    applies them in an isolated memory buffer, and the **Critic Agent** re-runs accessibility validation with adaptive retry strategies to guarantee
    zero regressions before developer sign-off.
    """)

    if "audit" in st.session_state and st.session_state.audit.get("remediations"):
        remediations = st.session_state.audit["remediations"]
        diff_text = st.session_state.audit.get("diff", "")

        c1, c2 = st.columns(2)
        applied_count = sum(1 for r in remediations if r.retest_resolved)
        c1.metric("Verified Resolved Fixes", applied_count)
        c2.metric("Manual Review Required", len(remediations) - applied_count)

        if diff_text:
            st.markdown("#### 🔄 Unified Diff (Original vs. Patched Sandbox)")
            st.code(diff_text, language="diff")

        st.markdown("#### Detailed Patch Review")
        for idx, rem in enumerate(remediations):
            with st.expander(f"Patch #{idx+1} for Rule `{rem.rule_id}` (Status: {rem.status}) — Strategy: `{rem.strategy_used}`"):
                st.write(f"**Critic Verdict**: {rem.critic_notes}")
                col_orig, col_fix = st.columns(2)
                col_orig.markdown("**Original Snippet**:")
                col_orig.code(rem.original_snippet, language="html")
                col_fix.markdown("**Proposed Fix**:")
                col_fix.code(rem.proposed_snippet, language="html")

                c_accept, c_reject = st.columns(2)
                c_accept.checkbox(f"Approve Fix #{idx+1}", value=rem.retest_resolved, key=f"approve_{rem.finding_id}")
                c_reject.checkbox(f"Reject / Request Custom Edit #{idx+1}", value=not rem.retest_resolved, key=f"reject_{rem.finding_id}")

        if st.session_state.audit.get("patched_html"):
            st.download_button(
                "💾 Download Patched HTML",
                st.session_state.audit["patched_html"],
                "patched_page.html",
                "text/html",
                use_container_width=True,
            )
    else:
        st.info("Run an audit on a page with violations to inspect the remediation sandbox and before/after diffs.")

# --- TAB 3: EVALUATION BENCHMARK ---
with tab_benchmark:
    st.subheader("📊 Quantitative Evaluation Benchmark")
    st.markdown("""
    AccessAble AI is evaluated against a curated suite of 18 synthetic ground-truth test fixtures.
    The benchmark quantifies real **Precision**, **Recall**, **F1-Score**, and **Fix Retest Pass Rates**.
    """)

    if st.button("⚡ Run Live Benchmark Evaluation", type="secondary"):
        with st.spinner("Evaluating across 18 synthetic ground-truth test fixtures..."):
            b_results = run_benchmark()
            st.session_state.benchmark_results = b_results

    if "benchmark_results" in st.session_state:
        br = st.session_state.benchmark_results
        bc1, bc2, bc3, bc4, bc5 = st.columns(5)
        bc1.metric("Tested Fixtures", br["total_fixtures"])
        bc2.metric("Precision", f"{br['precision'] * 100:.1f}%")
        bc3.metric("Recall", f"{br['recall'] * 100:.1f}%")
        bc4.metric("F1-Score", f"{br['f1_score']:.4f}")
        bc5.metric("Fix Pass Rate", f"{br['fix_success_rate'] * 100:.1f}%")

        st.markdown("#### Ground-Truth Fixture Breakdown")
        df_fixtures = pd.DataFrame(br["fixture_results"])
        st.dataframe(df_fixtures[["id", "category", "description", "pass", "tp", "fp", "fn"]], use_container_width=True)
        st.caption(f"Benchmark executed deterministically in {br['execution_time_seconds']} seconds.")
    else:
        st.info("Click **Run Live Benchmark Evaluation** to execute the quantitative benchmark test suite.")

# --- TAB 4: AGENT ORCHESTRATION TRACE ---
with tab_trace:
    st.subheader("🤖 Agent State Machine & Adaptive Retries")

    st.graphviz_chart('''digraph {
      rankdir=LR;
      node [shape=box, style="rounded,filled", fillcolor="#EFF6FF", color="#2563EB", fontname="sans-serif"];
      input [label="Input Gateway\nHTML / Upload / URL"];
      planner [label="Agent 0: Planner\nSSRF Guard & Engine"];
      scanner [label="Agent 1: Scanner\nDOM / Axe Engine"];
      standards [label="Agent 2: Standards Analyst\nWCAG 2.2 Mapping"];
      remediate [label="Agent 3: Remediation\nAdaptive Synthesizer"];
      critic [label="Agent 4: Critic & Retest\nIsolated Sandbox"];
      human [label="Agent 5: Validation Boundary\nHuman Review Checklist"];

      input -> planner -> scanner -> standards -> remediate -> critic;
      critic -> remediate [label="Adaptive Strategy Retry", color="#DC2626", style=dashed];
      critic -> human [label="Passed Verification", color="#16A34A"];
    }''', use_container_width=True)

    if "audit" in st.session_state and st.session_state.audit.get("agent_trace"):
        st.markdown("#### Live Execution Step Log")
        for step in st.session_state.audit["agent_trace"]:
            st.markdown(f"**[{step['agent']}]** `{step['action']}`: {step['details']}")

        if st.session_state.audit.get("retry_history"):
            st.markdown("#### 🔄 Adaptive Critic Retry History")
            for rec in st.session_state.audit["retry_history"]:
                st.info(f"**Iteration {rec.iteration}** ({rec.candidate_id}): {rec.changed_action} — **Result**: {rec.critic_feedback}")
    else:
        st.info("Run an audit to view live state transitions and agent decisions.")

# --- TAB 5: AUDIT HISTORY ---
with tab_history:
    st.subheader("📜 Recent Local Audit Runs")
    history_records = get_audit_history(limit=15)
    if history_records:
        df_hist = pd.DataFrame(history_records)
        df_hist["date"] = pd.to_datetime(df_hist["timestamp"], unit="s").dt.strftime("%Y-%m-%d %H:%M:%S")
        st.dataframe(
            df_hist[["id", "date", "input_source", "input_fingerprint", "finding_count", "high_count", "resolved_fix_count", "retry_iterations", "engine_mode", "status"]],
            use_container_width=True
        )
    else:
        st.info("No prior audit history recorded in local database.")

# --- TAB 6: ABOUT & LIMITATIONS ---
with tab_about:
    st.subheader("📖 Project Scope & Technical Limitations")
    st.markdown("""
    ### Honest Engineering Scope
    AccessAble AI provides automated accessibility detection and context-aware remediation guidance.
    
    **What It Does:**
    - Deterministically parses HTML DOM and styles according to WCAG 2.2 rules.
    - Integrates headless Playwright with axe-core for rendered DOM and computed style inspection.
    - Synthesizes adaptive non-destructive code patches in a sandboxed memory buffer with regression verification.
    - Implements defense-in-depth SSRF protections to prevent internal network scanning and subresource traversal.

    **What It Does Not Do:**
    - It does **not** certify complete WCAG 2.2 compliance (only ~30-40% of WCAG criteria can be reliably automated).
    - It does **not** replace real assistive technology user testing (screen readers like NVDA/VoiceOver).
    - It does **not** silently overwrite live production servers.
    """)
