import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const workspaceDir = process.cwd();
const skillDir = "C:/Users/ppriy/.codex/plugins/cache/openai-primary-runtime/presentations/26.1015.12040/skills/presentations";
const buildDir = path.join(workspaceDir, ".build", "ppt");
const finalPath = path.join(workspaceDir, "deliverables", "AccessAble_AI_CA3_Presentation.pptx");
await fs.mkdir(buildDir, { recursive: true });
await fs.mkdir(path.dirname(finalPath), { recursive: true });

const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const navy = "#123B5D", blue = "#2463A5", pale = "#EAF2FF", ink = "#102A43", muted = "#52677A", green = "#117B50", orange = "#B7791F", white = "#FFFFFF";
const page = { left: 76, top: 54, width: 1128, height: 612 };

function shape(slide, geometry, position, fill = "none", line = "none") {
  return slide.shapes.add({ geometry, position, fill, line: { style: "solid", fill: line, width: line === "none" ? 0 : 1 } });
}
function text(slide, value, position, size = 20, color = ink, bold = false, align = "left") {
  const box = shape(slide, "textbox", position);
  box.text = value;
  box.text.style = { fontSize: size, fontFace: "Aptos", color, bold, align, breakLine: false };
  return box;
}
function base(title, number) {
  const slide = deck.slides.add();
  slide.background.fill = "#F8FBFE";
  shape(slide, "rect", { left: 0, top: 0, width: 1280, height: 12 }, navy);
  text(slide, title, { left: page.left, top: page.top, width: 900, height: 48 }, 31, navy, true);
  text(slide, `CA-3  |  Priyansh Pandey  |  ${number}/7`, { left: 920, top: 64, width: 280, height: 22 }, 12, muted, false, "right");
  return slide;
}
function bullet(slide, value, y, width = 500, x = 94, size = 19) {
  text(slide, "•", { left: x, top: y, width: 18, height: 26 }, size, blue, true);
  text(slide, value, { left: x + 25, top: y, width, height: 50 }, size, ink);
}
function node(slide, label, x, y, w = 142, h = 64, fill = pale, color = blue) {
  shape(slide, "roundRect", { left: x, top: y, width: w, height: h }, fill, color);
  text(slide, label, { left: x + 7, top: y + 12, width: w - 14, height: h - 20 }, 13, ink, true, "center");
}

// 1
{
  const slide = deck.slides.add(); slide.background.fill = "#F8FBFE";
  shape(slide, "rect", { left: 0, top: 0, width: 1280, height: 720 }, "#F4F9FF");
  shape(slide, "rect", { left: 0, top: 0, width: 420, height: 720 }, navy);
  text(slide, "AccessAble\nAI", { left: 78, top: 150, width: 300, height: 150 }, 52, white, true);
  text(slide, "Multi-Agent Website\nAccessibility Auditor", { left: 78, top: 330, width: 280, height: 90 }, 23, "#C7DDF4", false);
  text(slide, "CA-3 Agentic AI Proof of Concept\nPriyansh Pandey\nOctober 2026", { left: 78, top: 520, width: 290, height: 96 }, 16, white);
  text(slide, "A focused first-pass audit for common HTML accessibility barriers", { left: 500, top: 180, width: 640, height: 80 }, 35, navy, true);
  text(slide, "The PoC combines deterministic checks, WCAG context, fix guidance, and an explicit human-review boundary.", { left: 500, top: 300, width: 620, height: 80 }, 22, muted);
  node(slide, "Missing alt text", 500, 470, 180, 70, "#FFF2F2", "#C53030");
  node(slide, "Unlabelled form", 720, 470, 180, 70, "#FFF8E7", orange);
  node(slide, "Low contrast", 940, 470, 180, 70, "#FFF2F2", "#C53030");
}

// 2
{
  const slide = base("Accessibility review challenge and solution", 2);
  text(slide, "Current challenge", { left: 94, top: 140, width: 390, height: 32 }, 21, blue, true);
  bullet(slide, "Small teams can miss basic HTML barriers during routine development.", 190, 430);
  bullet(slide, "Manual review remains essential and needs specialist time.", 280, 430);
  bullet(slide, "Raw rule failures do not tell a developer how to fix the page.", 370, 430);
  shape(slide, "roundRect", { left: 620, top: 140, width: 490, height: 385 }, white, "#B9D1E8");
  text(slide, "AccessAble AI response", { left: 660, top: 180, width: 390, height: 32 }, 21, green, true);
  text(slide, "Submitted HTML", { left: 700, top: 245, width: 160, height: 30 }, 18, ink, true, "center");
  text(slide, "Structured agent workflow", { left: 700, top: 315, width: 280, height: 30 }, 18, ink, true, "center");
  text(slide, "Severity report, fixes, CSV and human review", { left: 660, top: 400, width: 390, height: 50 }, 18, ink, true, "center");
  text(slide, "The tool supports an initial QA review. It does not certify WCAG conformance.", { left: 94, top: 570, width: 1010, height: 32 }, 18, muted);
}

// 3
{
  const slide = base("Agent roles and data flow", 3);
  const labels = ["User and\nStreamlit UI", "Planner\nselect checks", "Scanner\nHTML signals", "Standards\nWCAG map", "Fix Agent\nremediation", "Validation\nhuman boundary", "Critic\ncomplete report"];
  labels.forEach((label, i) => node(slide, label, 78 + i * 160, 190, 132, 74, i === 6 ? "#E7F8F0" : pale, i === 6 ? green : blue));
  for (let i = 0; i < 6; i++) text(slide, "→", { left: 212 + i * 160, top: 210, width: 22, height: 30 }, 24, blue, true, "center");
  text(slide, "Inputs", { left: 95, top: 330, width: 170, height: 30 }, 19, blue, true);
  text(slide, "Synthetic sample page or pasted HTML", { left: 95, top: 370, width: 250, height: 50 }, 17, ink);
  text(slide, "Supporting knowledge", { left: 430, top: 330, width: 250, height: 30 }, 19, blue, true);
  text(slide, "WCAG 2.2 mappings and transparent deterministic rules", { left: 430, top: 370, width: 280, height: 50 }, 17, ink);
  text(slide, "Outputs", { left: 805, top: 330, width: 170, height: 30 }, 19, blue, true);
  text(slide, "Findings by severity, CSV export, and human-review checklist", { left: 805, top: 370, width: 300, height: 50 }, 17, ink);
  text(slide, "Every stage hands structured output to the next stage. The code uses deterministic Python agents, not a hidden external model.", { left: 94, top: 540, width: 1040, height: 42 }, 18, muted);
}

// 4
{
  const slide = base("Technology stack and implementation", 4);
  const items = [["Python 3.10", "Agent logic and tests"], ["Streamlit", "Interactive QA interface"], ["html.parser", "Supplied HTML parsing"], ["pandas", "CSV export"], ["unittest", "Repeatable verification"]];
  items.forEach(([name, purpose], i) => {
    const y = 142 + i * 72;
    shape(slide, "roundRect", { left: 94, top: y, width: 250, height: 52 }, pale, "#B9D1E8");
    text(slide, name, { left: 112, top: y + 13, width: 205, height: 26 }, 18, navy, true);
    text(slide, purpose, { left: 390, top: y + 13, width: 300, height: 28 }, 19, ink);
  });
  shape(slide, "roundRect", { left: 760, top: 145, width: 350, height: 330 }, white, "#B9D1E8");
  text(slide, "Implemented checks", { left: 800, top: 185, width: 280, height: 34 }, 22, blue, true, "center");
  text(slide, "IMG_ALT\nFORM_LABEL\nPAGE_LANG\nPAGE_TITLE\nCOLOR_CONTRAST", { left: 830, top: 245, width: 220, height: 160 }, 18, ink, true, "center");
  text(slide, "No paid API or external LLM dependency", { left: 785, top: 520, width: 310, height: 32 }, 18, green, true, "center");
}

// 5
{
  const slide = base("Working PoC demonstration and results", 5);
  text(slide, "Demo flow: select a synthetic page, run audit, inspect evidence and fixes, then download CSV.", { left: 94, top: 125, width: 1000, height: 34 }, 18, muted);
  slide.charts.add("bar", { position: { left: 100, top: 205, width: 520, height: 300 }, categories: ["Broken store page", "Improved store page"], series: [{ name: "Findings", values: [5, 0], fill: blue }], hasLegend: false, dataLabels: { showValue: true, position: "outEnd" }, yAxis: { majorGridlines: { style: "solid", fill: "#D9E6F2", width: 1 } } });
  shape(slide, "roundRect", { left: 700, top: 205, width: 410, height: 280 }, white, "#B9D1E8");
  text(slide, "Broken page output", { left: 735, top: 235, width: 320, height: 32 }, 21, "#C53030", true, "center");
  text(slide, "3 High\n2 Medium\n5 Total", { left: 800, top: 300, width: 200, height: 105 }, 26, navy, true, "center");
  text(slide, "The improved page has zero findings under these five implemented rules.", { left: 94, top: 550, width: 980, height: 34 }, 18, muted);
}

// 6
{
  const slide = base("Validation boundary and human review", 6);
  text(slide, "What this PoC can check", { left: 100, top: 140, width: 390, height: 32 }, 22, green, true);
  bullet(slide, "Structural presence of selected HTML attributes and elements", 195, 440, 100, 18);
  bullet(slide, "Limited inline foreground and background contrast calculation", 285, 440, 100, 18);
  bullet(slide, "Whether each report contains standard, fix, and validation guidance", 375, 440, 100, 18);
  text(slide, "What a human must review", { left: 650, top: 140, width: 390, height: 32 }, 22, orange, true);
  bullet(slide, "Meaningful image descriptions in context", 195, 410, 650, 18);
  bullet(slide, "Keyboard operation, focus order, and visible focus", 285, 410, 650, 18);
  bullet(slide, "Screen-reader flow, dynamic updates, and cognitive clarity", 375, 410, 650, 18);
  text(slide, "Zero automated findings does not prove full accessibility or WCAG conformance.", { left: 100, top: 540, width: 980, height: 34 }, 20, navy, true, "center");
}

// 7
{
  const slide = base("Impact future scope and conclusion", 7);
  text(slide, "Current contribution", { left: 100, top: 145, width: 310, height: 34 }, 22, blue, true);
  bullet(slide, "A repeatable first-pass accessibility review for supplied HTML", 205, 440, 100, 18);
  bullet(slide, "Clear developer guidance tied to relevant WCAG criteria", 290, 440, 100, 18);
  bullet(slide, "A visible boundary between automation and human judgement", 375, 440, 100, 18);
  text(slide, "Future scope", { left: 680, top: 145, width: 260, height: 34 }, 22, green, true);
  bullet(slide, "Rendered browser and broader CSS checks", 205, 350, 680, 18);
  bullet(slide, "Batch audits and review history", 290, 350, 680, 18);
  bullet(slide, "Human approval workflow", 375, 350, 680, 18);
  text(slide, "AccessAble AI demonstrates transparent, testable agent collaboration for a practical web QA task.", { left: 100, top: 545, width: 1000, height: 38 }, 22, navy, true, "center");
}

const candidatePath = path.join(buildDir, "AccessAble_AI_CA3_Presentation_candidate.pptx");
await (await PresentationFile.exportPptx(deck)).save(candidatePath);
const { finalizePresentation } = await import(pathToFileURL(path.join(skillDir, "container_tools", "artifact_tool_utils.mjs")).href);
const result = await finalizePresentation({
  explicitTotalSlideCount: 7,
  workspaceDir,
  candidatePath,
  finalPath,
  pythonExecutable: "C:/Users/ppriy/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe",
  integrityValidatorPath: path.join(skillDir, "container_tools", "inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(skillDir, "container_tools", "inspect_presentation_layout_geometry.py"),
  layoutArgs: ["--expected-slide-size-emu", "12192000,6858000", "--validate-bullet-geometry", "--validate-heading-fit"],
  requiredNativeTableOwnerSlides: [],
  materializeLiteralChartWorkbooks: true,
  fontPolicy: { basis: "design", families: ["Aptos", "Aptos Display"] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(buildDir, "presentation_validation.json"),
});
console.log(JSON.stringify(result, null, 2));
