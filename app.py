"""AccessAble AI NiceGUI glassmorphism interface. Core audit logic remains in core/."""
from __future__ import annotations
import csv, io, json, os
from datetime import datetime
from typing import Any
from dotenv import load_dotenv
from nicegui import run, ui
load_dotenv()
from audit_engine import findings_to_rows, run_audit
from benchmark.evaluator import run_benchmark
from core.database import get_audit_history
from core.gemini_critic import is_gemini_available
from sample_pages import BROKEN_STORE_PAGE, IMPROVED_STORE_PAGE

ui.colors(primary="#8b5cf6", secondary="#22d3ee", accent="#a78bfa", dark="#080b16", positive="#34d399", negative="#fb7185", warning="#fbbf24")
ui.add_head_html("""
<meta name="viewport" content="width=device-width, initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root{--bg:#080b16;--panel:rgba(17,24,43,.82);--line:rgba(148,163,184,.16);--muted:#94a3b8;--text:#eef2ff}
html,body{background:radial-gradient(ellipse at 10% 0%,#211448 0,transparent 34%),radial-gradient(ellipse at 95% 12%,#0d3041 0,transparent 32%),var(--bg)!important;color:var(--text)!important;font-family:Inter,system-ui,sans-serif!important}
.q-page{background:transparent!important}.glass{background:linear-gradient(135deg,rgba(24,31,54,.86),rgba(12,18,33,.82));border:1px solid var(--line);border-radius:20px;backdrop-filter:blur(18px);box-shadow:0 18px 55px rgba(0,0,0,.2)}
.metric{padding:18px 20px;min-height:100px}.metric-label{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.12em;font-weight:700}.metric-value{font-size:30px;font-weight:800;letter-spacing:-.04em;margin-top:6px}
.hero{font-size:clamp(30px,4vw,48px);font-weight:800;letter-spacing:-.055em;background:linear-gradient(100deg,#f8fafc 5%,#c4b5fd 45%,#67e8f9 100%);-webkit-background-clip:text;background-clip:text;color:transparent}
.muted{color:var(--muted)}.pill{display:inline-block;padding:4px 10px;border:1px solid var(--line);border-radius:999px;font-size:11px;color:#c4b5fd;background:rgba(139,92,246,.12)}
.issue{padding:16px;border-radius:14px;background:rgba(255,255,255,.025);border:1px solid var(--line)}.q-field--outlined .q-field__control:before{border-color:rgba(148,163,184,.24)!important}.q-field__label,.q-field__native,.q-field__input{color:#e2e8f0!important}.q-tab{color:#94a3b8!important;font-weight:600}.q-tab--active{color:#c4b5fd!important}.q-tab__indicator{background:#a78bfa!important}.q-btn{border-radius:11px!important;font-weight:700!important}.q-table{background:transparent!important;color:#e2e8f0!important}.q-table thead tr{color:#a5b4fc!important}pre{white-space:pre-wrap;overflow-wrap:anywhere}
</style>""")
ui.page_title("AccessAble AI | Accessibility Command Center")
ui.dark_mode().enable()
state: dict[str, Any] = {"result": None, "filter": "All"}

def fv(item: Any, key: str, default: Any = "") -> Any:
    return item.get(key, default) if isinstance(item, dict) else getattr(item, key, default)

def notify(message: str, kind: str = "info") -> None:
    ui.notify(message, type=kind, position="top")

def metric(label: str, value: Any, detail: str = "") -> None:
    with ui.column().classes("glass metric flex-1 gap-0"):
        ui.label(label).classes("metric-label")
        ui.label(str(value)).classes("metric-value")
        if detail: ui.label(detail).classes("muted text-xs")

def findings() -> list[Any]:
    return (state.get("result") or {}).get("findings", []) or []

def render_findings() -> None:
    findings_area.clear()
    all_findings = findings()
    shown = [f for f in all_findings if state["filter"] == "All" or fv(f, "severity") == state["filter"]]
    with findings_area:
        if not all_findings:
            ui.label("Run an audit to inspect accessibility barriers.").classes("muted")
            return
        with ui.row().classes("w-full items-center justify-between"):
            ui.label(f"{len(shown)} findings").classes("font-semibold")
            ui.select(["All","High","Medium","Low"], value=state["filter"], label="Severity",
                      on_change=lambda e: change_filter(e.value)).classes("w-40")
        for f in shown:
            level = str(fv(f,"severity","Low"))
            color = {"High":"#fb7185","Medium":"#fbbf24","Low":"#67e8f9"}.get(level,"#94a3b8")
            with ui.column().classes("issue w-full gap-2"):
                with ui.row().classes("w-full items-center justify-between"):
                    ui.label(str(fv(f,"title",fv(f,"rule_id","Accessibility issue")))).classes("font-bold")
                    ui.label(level.upper()).style(f"color:{color};font-size:11px;font-weight:800")
                ui.label(f"{fv(f,'rule_id')} · {fv(f,'wcag_criterion','WCAG criterion not specified')}").classes("muted text-xs")
                ui.label(str(fv(f,"why_it_matters",""))).classes("text-sm")
                with ui.expansion("Evidence and recommended fix").classes("w-full"):
                    ui.label("Evidence").classes("text-xs font-bold muted")
                    ui.code(str(fv(f,"evidence","")), language="html").classes("w-full")
                    ui.label("Recommendation").classes("text-xs font-bold muted mt-2")
                    ui.label(str(fv(f,"recommendation",""))).classes("text-sm")
                    patch = fv(f,"remediation_patch","")
                    if patch: ui.code(str(patch), language="html").classes("w-full")

def change_filter(value: str) -> None:
    state["filter"] = value
    render_findings()

def render_trace() -> None:
    trace_area.clear()
    trace = (state.get("result") or {}).get("agent_trace", []) or []
    with trace_area:
        if not trace:
            ui.label("Agent trace appears after an audit.").classes("muted")
            return
        for i, item in enumerate(trace, 1):
            with ui.row().classes("items-start w-full gap-3"):
                ui.label(str(i)).classes("pill")
                with ui.column().classes("gap-1 flex-1"):
                    ui.label(str(fv(item,"agent",fv(item,"agent_name","Agent")))).classes("font-semibold")
                    ui.label(str(fv(item,"action",fv(item,"step","")))).classes("text-sm")
                    ui.label(str(fv(item,"detail",fv(item,"message","")))).classes("muted text-xs")

def render_remediation() -> None:
    remediation_area.clear()
    result = state.get("result") or {}
    with remediation_area:
        if not result:
            ui.label("Run an audit to see proposed fixes and retest results.").classes("muted")
            return
        remediations = result.get("remediations", []) or []
        if not remediations: ui.label("No remediation candidates generated.").classes("muted")
        for rem in remediations:
            with ui.column().classes("issue w-full gap-2"):
                ui.label(f"{fv(rem,'rule_id','Fix')} · {'Verified' if fv(rem,'retest_resolved',False) else 'Human review / unresolved'}").classes("font-semibold")
                ui.label(str(fv(rem,"critic_notes","No critic note recorded."))).classes("muted text-sm")
                with ui.expansion("View proposed HTML change"):
                    ui.code(str(fv(rem,"original_snippet","")), language="html").classes("w-full")
                    ui.icon("arrow_downward", color="secondary")
                    ui.code(str(fv(rem,"proposed_snippet","")), language="html").classes("w-full")
        if result.get("diff"):
            ui.label("Unified diff").classes("font-bold")
            ui.code(str(result["diff"]), language="diff").classes("w-full")
        for item in result.get("human_checks", []): ui.checkbox(str(item), value=False)

async def run_audit() -> None:
    source = source_select.value
    target_url = url_input.value.strip() if source == "Public URL" else None
    html = html_input.value or ""
    if source == "Broken demo page": html = BROKEN_STORE_PAGE
    elif source == "Improved demo page": html = IMPROVED_STORE_PAGE
    elif source == "Uploaded HTML file": html = uploaded_html.value or ""
    elif source == "Public URL":
        html = ""
        if not target_url:
            notify("Enter a public website URL first.", "warning"); return
    elif not html.strip():
        notify("Paste HTML before running an audit.", "warning"); return
    run_button.disable()
    try:
        result = await run.io_bound(__import__("audit_engine").run_audit, html, bool(browser_toggle.value), target_url)
        state["result"] = result
        counts = result.get("counts") or {k: sum(fv(f,"severity")==k for f in result.get("findings",[])) for k in ["High","Medium","Low"]}
        total_metric.set_text(str(len(result.get("findings",[]))))
        high_metric.set_text(str(counts.get("High",0))); medium_metric.set_text(str(counts.get("Medium",0))); low_metric.set_text(str(counts.get("Low",0)))
        audit_status.set_text(str(result.get("status","complete")).upper())
        audit_id.set_text("Audit ID: " + str(result.get("audit_id","—")))
        render_findings(); render_trace(); render_remediation()
        notify("Audit completed." if result.get("status") != "error" else result.get("message","Audit failed."), "positive" if result.get("status") != "error" else "negative")
    except Exception as exc:
        notify(f"Audit failed: {exc}", "negative")
    finally:
        run_button.enable()

def export_csv() -> None:
    rows = findings_to_rows(findings())
    if not rows: notify("Run an audit before exporting.", "warning"); return
    output = io.StringIO(); writer = csv.DictWriter(output, fieldnames=list(rows[0].keys())); writer.writeheader(); writer.writerows(rows)
    ui.download(output.getvalue().encode(), "accessable-findings.csv", "text/csv")

def export_json() -> None:
    result = state.get("result")
    if not result: notify("Run an audit before exporting.", "warning"); return
    safe = dict(result)
    safe["findings"] = [f.to_dict() if hasattr(f,"to_dict") else f for f in result.get("findings",[])]
    safe["remediations"] = [r.__dict__ if hasattr(r,"__dict__") else r for r in result.get("remediations",[])]
    ui.download(json.dumps(safe, indent=2, default=str).encode(), "accessable-audit-report.json", "application/json")

with ui.row().classes("w-full items-center justify-between px-4 py-3"):
    with ui.row().classes("items-center gap-3"):
        with ui.element("div").classes("rounded-2xl p-3").style("background:linear-gradient(135deg,#7c3aed,#0891b2)"):
            ui.icon("accessibility_new", size="28px", color="white")
        with ui.column().classes("gap-0"):
            ui.label("ACCESSABLE AI").classes("font-extrabold tracking-widest text-sm")
            ui.label("MULTI-AGENT ACCESSIBILITY AUDITOR").classes("muted text-xs tracking-wider")
    with ui.row().classes("items-center gap-2"):
        ui.label("GEMINI CRITIC").classes("muted text-xs font-bold")
        ui.label("CONFIGURED" if is_gemini_available() else "FALLBACK MODE").classes("pill")
        ui.label("● SYSTEM READY").style("color:#34d399;font-size:11px;font-weight:800")
ui.separator().classes("opacity-20")
with ui.column().classes("w-full max-w-7xl mx-auto px-4 md:px-8 py-6 gap-6"):
    ui.label("Accessibility, orchestrated.").classes("hero")
    ui.label("Find barriers. Understand WCAG impact. Review safe fixes. Validate before you ship.").classes("muted text-base")
    with ui.row().classes("w-full gap-2 flex-wrap"):
        for name in ["PLANNER","SCANNER","WCAG ANALYST","FIX RECOMMENDER","GEMINI CRITIC","RETEST"]: ui.label(name).classes("pill")
    with ui.tabs().classes("w-full") as tabs:
        audit_tab=ui.tab("Audit workspace",icon="travel_explore")
        remediation_tab=ui.tab("Remediation sandbox",icon="difference")
        benchmark_tab=ui.tab("Benchmark",icon="query_stats")
        trace_tab=ui.tab("Agent trace",icon="account_tree")
        history_tab=ui.tab("Audit history",icon="history")
        about_tab=ui.tab("About",icon="info")
    with ui.tab_panels(tabs,value=audit_tab).classes("w-full bg-transparent"):
        with ui.tab_panel(audit_tab):
            with ui.row().classes("w-full items-stretch gap-4 flex-wrap"):
                with ui.column().classes("glass p-5 gap-4").style("flex:1 1 320px"):
                    ui.label("Configure an audit").classes("text-lg font-bold")
                    source_select=ui.select(["Broken demo page","Improved demo page","Paste HTML","Uploaded HTML file","Public URL"],value="Broken demo page",label="Input source").classes("w-full")
                    url_input=ui.input("Public website URL",placeholder="https://example.com").classes("w-full")
                    html_input=ui.textarea("HTML source",placeholder="Paste page HTML here…").props("rows=8").classes("w-full")
                    uploaded_html=ui.textarea("Uploaded HTML content",placeholder="Upload an .html file below").props("rows=3").classes("w-full")
                    ui.upload(label="Upload HTML file",auto_upload=True,on_upload=lambda e:uploaded_html.set_value(e.content.read().decode("utf-8",errors="replace"))).props("accept=.html,.htm").classes("w-full")
                    browser_toggle=ui.checkbox("Use browser + axe-core scan",value=False)
                    run_button=ui.button("Run accessibility audit",icon="play_arrow",on_click=run_audit).props("color=primary unelevated").classes("w-full")
                    ui.label("Public URL scans use the existing URL security checks.").classes("muted text-xs")
                with ui.column().classes("gap-4").style("flex:2 1 500px"):
                    with ui.row().classes("w-full gap-3 flex-wrap"):
                        with ui.column().classes("glass metric flex-1").style("min-width:120px"):
                            ui.label("TOTAL FINDINGS").classes("metric-label"); total_metric=ui.label("0").classes("metric-value")
                        with ui.column().classes("glass metric flex-1").style("min-width:120px"):
                            ui.label("HIGH SEVERITY").classes("metric-label"); high_metric=ui.label("0").classes("metric-value").style("color:#fb7185")
                        with ui.column().classes("glass metric flex-1").style("min-width:120px"):
                            ui.label("MEDIUM").classes("metric-label"); medium_metric=ui.label("0").classes("metric-value").style("color:#fbbf24")
                        with ui.column().classes("glass metric flex-1").style("min-width:120px"):
                            ui.label("LOW").classes("metric-label"); low_metric=ui.label("0").classes("metric-value").style("color:#67e8f9")
                    with ui.column().classes("glass p-5 w-full gap-3"):
                        with ui.row().classes("w-full items-center justify-between"):
                            ui.label("Detected accessibility barriers").classes("text-lg font-bold"); audit_status=ui.label("READY").classes("pill")
                        audit_id=ui.label("Audit ID: —").classes("muted text-xs")
                        findings_area=ui.column().classes("w-full gap-3")
                        with ui.row().classes("w-full gap-2 flex-wrap"):
                            ui.button("Export findings CSV",icon="download",on_click=export_csv).props("outline color=secondary")
                            ui.button("Export report JSON",icon="description",on_click=export_json).props("outline color=secondary")
        with ui.tab_panel(remediation_tab):
            with ui.column().classes("glass p-5 w-full gap-3"):
                ui.label("Safe remediation sandbox").classes("text-xl font-bold")
                ui.label("Review proposed changes, critic notes, retest status, and manual verification tasks. Automated checks do not replace assistive-technology testing.").classes("muted")
                remediation_area=ui.column().classes("w-full gap-3")
        with ui.tab_panel(benchmark_tab):
            with ui.column().classes("glass p-5 w-full gap-4"):
                ui.label("Quantitative benchmark").classes("text-xl font-bold")
                ui.label("Run the ground-truth fixture suite against the deterministic scanner and remediation validator.").classes("muted")
                benchmark_output=ui.column().classes("w-full gap-3")
                async def run_benchmark_ui() -> None:
                    benchmark_button.disable()
                    try:
                        report=await ui.run.io_bound(run_benchmark); benchmark_output.clear()
                        with benchmark_output:
                            with ui.row().classes("w-full gap-3 flex-wrap"):
                                metric("Fixtures",report["total_fixtures"]); metric("Precision",f'{report["precision"]*100:.1f}%')
                                metric("Recall",f'{report["recall"]*100:.1f}%'); metric("F1 score",f'{report["f1_score"]:.3f}')
                                metric("Fix success",f'{report["fix_success_rate"]*100:.1f}%')
                            ui.label(f'Execution time: {report["execution_time_seconds"]} seconds · Fixes: {report["total_fixes_succeeded"]}/{report["total_fixes_tested"]}').classes("muted text-sm")
                            ui.table(columns=[{"name":"id","label":"Fixture","field":"id"},{"name":"category","label":"Category","field":"category"},{"name":"pass","label":"Exact match","field":"pass"},{"name":"tp","label":"TP","field":"tp"},{"name":"fp","label":"FP","field":"fp"},{"name":"fn","label":"FN","field":"fn"}],rows=report["fixture_results"],row_key="id").classes("w-full")
                    except Exception as exc:
                        benchmark_output.clear()
                        with benchmark_output: ui.label(f"Benchmark failed: {exc}").style("color:#fb7185")
                    finally: benchmark_button.enable()
                benchmark_button=ui.button("Run benchmark suite",icon="play_circle",on_click=run_benchmark_ui).props("color=primary unelevated")
        with ui.tab_panel(trace_tab):
            with ui.column().classes("glass p-5 w-full gap-3"):
                ui.label("Agent execution trace").classes("text-xl font-bold")
                ui.label("Chronological steps recorded by the audit orchestrator.").classes("muted")
                trace_area=ui.column().classes("w-full gap-3")
        with ui.tab_panel(history_tab):
            with ui.column().classes("glass p-5 w-full gap-3"):
                ui.label("Recent audit history").classes("text-xl font-bold")
                ui.label("Only audit summaries and input fingerprints are stored by the existing SQLite layer.").classes("muted")
                history_table=ui.table(columns=[{"name":"timestamp","label":"Time","field":"timestamp"},{"name":"id","label":"Audit ID","field":"id"},{"name":"input_source","label":"Source","field":"input_source"},{"name":"finding_count","label":"Findings","field":"finding_count"},{"name":"high_count","label":"High","field":"high_count"},{"name":"medium_count","label":"Medium","field":"medium_count"},{"name":"low_count","label":"Low","field":"low_count"},{"name":"status","label":"Status","field":"status"}],rows=[],row_key="id").classes("w-full")
                def refresh_history() -> None:
                    rows=get_audit_history(50)
                    for row in rows: row["timestamp"]=datetime.fromtimestamp(row["timestamp"]).strftime("%d %b %Y, %H:%M")
                    history_table.rows=rows; history_table.update()
                ui.button("Refresh history",icon="refresh",on_click=refresh_history).props("outline color=secondary")
        with ui.tab_panel(about_tab):
            with ui.column().classes("glass p-5 w-full gap-3"):
                ui.label("About AccessAble AI").classes("text-xl font-bold")
                ui.label("A multi-agent accessibility auditing prototype for common WCAG 2.2 barriers. Automated findings are not a certification of conformance.").classes("muted")
                with ui.row().classes("w-full gap-3 flex-wrap"):
                    metric("Standards","WCAG 2.2","Supported automated rules"); metric("Scan engines","DOM + axe","Browser engine is optional"); metric("Human review","Required","Keyboard and screen-reader checks")
                for rule,desc in [("IMG_ALT","Text alternatives for non-text content."),("FORM_LABEL","Accessible names for form controls."),("COLOR_CONTRAST","Text contrast thresholds."),("PAGE_LANG","Document language."),("PAGE_TITLE","Descriptive page title."),("HEADING_ORDER","Meaningful heading structure."),("LINK_DISCERNIBLE","Link purpose and discernible text.")]:
                    with ui.row().classes("items-start gap-3"): ui.label(rule).classes("pill"); ui.label(desc).classes("text-sm")
                ui.label("Manual keyboard, screen-reader, and contextual testing remain necessary.").classes("muted text-sm mt-3")

with findings_area: ui.label("Run an audit to inspect accessibility barriers.").classes("muted")
with remediation_area: ui.label("Run an audit to see proposed fixes and retest results.").classes("muted")
with trace_area: ui.label("Agent trace appears after an audit.").classes("muted")
ui.run(host="0.0.0.0",port=int(os.environ.get("PORT","8080")),title="AccessAble AI",reload=False,show=False)
