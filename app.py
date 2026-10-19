import pandas as pd
import streamlit as st

from audit_engine import findings_to_rows, run_audit
from sample_pages import BROKEN_STORE_PAGE, IMPROVED_STORE_PAGE

st.set_page_config(page_title="AccessAble AI", page_icon="♿", layout="wide")

st.title("♿ AccessAble AI")
st.caption("Multi-Agent Website Accessibility Auditor — a transparent Streamlit proof of concept")

with st.sidebar:
    st.header("Demo controls")
    sample = st.selectbox("Load a demo page", ["Broken store page", "Improved store page", "Custom HTML"])
    st.info("Automated checks find common barriers. Human testing is still essential.")

defaults = {"Broken store page": BROKEN_STORE_PAGE, "Improved store page": IMPROVED_STORE_PAGE, "Custom HTML": "<!doctype html>\n<html lang=\"en\">\n<head><title>My page</title></head>\n<body>\n  <h1>Hello</h1>\n</body>\n</html>"}
html = st.text_area("HTML to audit", value=defaults[sample], height=300, help="Paste simple HTML or use a supplied synthetic demo.")

if st.button("Run multi-agent audit", type="primary", width="stretch"):
    try:
        st.session_state.audit = run_audit(html)
        st.session_state.audited_html = html
    except Exception as exc:
        st.error(f"The audit stopped unexpectedly: {exc}")

if "audit" not in st.session_state:
    st.info("Choose a demo page, then select **Run multi-agent audit**.")
    st.stop()

audit = st.session_state.audit
if audit["status"] == "no_input":
    st.warning(audit["message"])
    st.stop()
if audit["status"] == "error":
    st.error(audit["message"])
    st.stop()
st.subheader("Audit overview")
metrics = st.columns(4)
metrics[0].metric("Total findings", len(audit["findings"]))
metrics[1].metric("High", audit["counts"]["High"])
metrics[2].metric("Medium", audit["counts"]["Medium"])
metrics[3].metric("Planned rules", len(audit["plan"]["checks"]))

st.subheader("Agent orchestration")
st.graphviz_chart('''digraph {
  rankdir=LR; node [shape=box, style="rounded,filled", fillcolor="#E8F1FF", color="#1F5AA6"];
  input [label="HTML input\nor sample page"]; planner [label="0. Planner\nselect supported checks"]; scan [label="1. Scanner Agent\nDOM signals"]; standards [label="2. Standards Analyst\nWCAG mapping"]; fixes [label="3. Fix Recommendation\nimplementation guidance"]; validate [label="4. Validation Agent\nauto vs human review"]; critic [label="5. Critic\ncheck hand-off completeness"]; report [label="Findings report\nCSV + human checklist"];
  input -> planner -> scan -> standards -> fixes -> validate -> critic -> report;
}''', width="stretch")

with st.expander("Agent plan and critic review"):
    st.write(audit["plan"]["message"])
    st.write("Planned checks: " + ", ".join(audit["plan"]["checks"]))
    for note in audit["critic_notes"]:
        st.caption(note)

st.subheader("Findings by severity")
if not audit["findings"]:
    st.success("No issues were found by these automated rules. This is not a full accessibility conformance result.")
else:
    severity_order = ["High", "Medium", "Low"]
    for severity in severity_order:
        group = [item for item in audit["findings"] if item.severity == severity]
        if group:
            st.markdown(f"#### {severity} severity ({len(group)})")
            for item in group:
                with st.expander(f"{item.rule_id} — {item.title}"):
                    st.code(item.evidence, language="html")
                    st.write(item.why_it_matters)
                    st.info("Fix: " + item.recommendation)
                    st.caption("Validation: " + item.validation)

st.subheader("Validation boundary: human review required")
for check in audit["human_checks"]:
    st.checkbox(check, value=False, key=f"human_{check}")

rows = findings_to_rows(audit["findings"])
if rows:
    st.download_button("Download findings as CSV", pd.DataFrame(rows).to_csv(index=False), "accessible-ai-audit.csv", "text/csv")

with st.expander("Project scope and limitation"):
    st.write("This PoC models an agentic workflow: each agent receives the previous agent's structured output and adds a distinct decision layer. It demonstrates common deterministic checks using synthetic HTML. It does not crawl live websites, execute JavaScript, inspect complete CSS, or certify WCAG conformance. Human review and real assistive-technology testing remain mandatory.")
