"use strict";

const PYODIDE_VERSION = "0.29.5";
const PYODIDE_BASE = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;
const MAX_FILE_BYTES = 2 * 1024 * 1024;

const elements = {
  runtimeStatus: document.getElementById("runtimeStatus"),
  themeToggle: document.getElementById("themeToggle"),
  manuscriptInput: document.getElementById("manuscriptInput"),
  analyzeButton: document.getElementById("analyzeButton"),
  loadSampleButton: document.getElementById("loadSampleButton"),
  clearButton: document.getElementById("clearButton"),
  fileInput: document.getElementById("fileInput"),
  emptyState: document.getElementById("emptyState"),
  resultsContent: document.getElementById("resultsContent"),
  metricGrid: document.getElementById("metricGrid"),
  alertBox: document.getElementById("alertBox"),
  resultsTableBody: document.getElementById("resultsTableBody"),
  resultSubtitle: document.getElementById("resultSubtitle"),
  errorBox: document.getElementById("errorBox"),
  exportActions: document.getElementById("exportActions"),
  downloadJsonButton: document.getElementById("downloadJsonButton"),
  downloadMarkdownButton: document.getElementById("downloadMarkdownButton"),
};

let pyodide = null;
let lastReport = null;
let lastMarkdown = "";

function setRuntimeStatus(text, state = "") {
  elements.runtimeStatus.textContent = text;
  elements.runtimeStatus.className = `status-pill ${state}`.trim();
}

function showError(message) {
  elements.errorBox.textContent = message;
  elements.errorBox.classList.remove("hidden");
}

function clearError() {
  elements.errorBox.textContent = "";
  elements.errorBox.classList.add("hidden");
}

function setBusy(isBusy) {
  elements.analyzeButton.disabled = isBusy || !pyodide || !elements.manuscriptInput.value.trim();
  elements.analyzeButton.textContent = isBusy ? "Analyzing…" : "Analyze report";
}

function applyTheme(theme) {
  const safeTheme = theme === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = safeTheme;
  elements.themeToggle.setAttribute(
    "aria-label",
    safeTheme === "dark" ? "Switch to light theme" : "Switch to dark theme",
  );
}

function initializeTheme() {
  let saved = null;
  try {
    saved = localStorage.getItem("care-review-theme");
  } catch (error) {
    console.warn("Theme preference storage is unavailable.", error);
  }
  applyTheme(saved === "dark" ? "dark" : "light");
}

function switchPanel(panelId) {
  document.querySelectorAll(".panel").forEach((panel) => {
    panel.classList.toggle("active-panel", panel.id === panelId);
  });
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.panel === panelId);
  });
}

function createMetric(label, value) {
  const card = document.createElement("div");
  card.className = "metric";

  const labelNode = document.createElement("div");
  labelNode.className = "metric-label";
  labelNode.textContent = label;

  const valueNode = document.createElement("div");
  valueNode.className = "metric-value";
  valueNode.textContent = value;

  card.append(labelNode, valueNode);
  return card;
}

function statusClass(status) {
  if (status === "MET") return "status-met";
  if (status === "PARTIALLY_MET") return "status-partial";
  return "status-unmet";
}

function renderReport(report) {
  elements.metricGrid.replaceChildren(
    createMetric("Coverage", `${Number(report.overall_compliance_score).toFixed(1)}%`),
    createMetric("Met", String(report.items_met)),
    createMetric("Partial", String(report.items_partially_met)),
    createMetric("Unmet", String(report.items_unmet)),
    createMetric("Timeline", report.timeline_valid ? "Valid" : "Review"),
  );

  elements.resultsTableBody.replaceChildren();
  for (const item of report.item_evaluations || []) {
    const row = document.createElement("tr");

    const itemCell = document.createElement("td");
    itemCell.textContent = item.item_id;

    const sectionCell = document.createElement("td");
    sectionCell.textContent = item.section;

    const statusCell = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = `status-badge ${statusClass(item.status)}`;
    badge.textContent = item.status === "PARTIALLY_MET" ? "PARTIAL" : item.status;
    statusCell.appendChild(badge);

    const findingCell = document.createElement("td");
    const findings = Array.isArray(item.findings) ? item.findings : [];
    const recommendations = Array.isArray(item.recommendations) ? item.recommendations : [];
    findingCell.textContent = [...findings, ...recommendations.map((x) => `Recommendation: ${x}`)].join(" ");

    row.append(itemCell, sectionCell, statusCell, findingCell);
    elements.resultsTableBody.appendChild(row);
  }

  const phiCount = Array.isArray(report.phi_violations) ? report.phi_violations.length : 0;
  if (phiCount > 0) {
    elements.alertBox.textContent =
      `${phiCount} potential direct-identifier pattern${phiCount === 1 ? "" : "s"} detected. Review the source text before sharing or publication. This screen is not a de-identification determination.`;
    elements.alertBox.classList.remove("hidden");
  } else {
    elements.alertBox.classList.add("hidden");
    elements.alertBox.textContent = "";
  }

  elements.resultSubtitle.textContent = report.manuscript_title || "Checklist review";
  elements.emptyState.classList.add("hidden");
  elements.resultsContent.classList.remove("hidden");
  elements.exportActions.classList.remove("hidden");
}

async function initializePython() {
  try {
    setRuntimeStatus("Loading Python…");
    pyodide = await loadPyodide({ indexURL: PYODIDE_BASE });

    const sourceResponse = await fetch("./care_validator.py", { cache: "no-store" });
    if (!sourceResponse.ok) {
      throw new Error(`Unable to load validator source (HTTP ${sourceResponse.status}).`);
    }
    const source = await sourceResponse.text();
    pyodide.FS.writeFile("care_validator.py", source);

    await pyodide.runPythonAsync(`
import json
from care_validator import CARECaseReportValidator, format_markdown_report

_browser_validator = CARECaseReportValidator()

def browser_validate(raw_text):
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        payload = raw_text

    report = _browser_validator.validate(payload)
    return json.dumps({
        "report": report.to_dict(),
        "markdown": format_markdown_report(report),
    }, ensure_ascii=False)
`);

    setRuntimeStatus("Python ready", "ready");
    setBusy(false);
  } catch (error) {
    console.error(error);
    pyodide = null;
    setRuntimeStatus("Runtime unavailable", "error");
    showError("Python runtime failed to load. Check the network connection and reload the page.");
    setBusy(false);
  }
}

async function analyze() {
  const raw = elements.manuscriptInput.value.trim();
  if (!raw || !pyodide) return;

  clearError();
  setBusy(true);

  try {
    pyodide.globals.set("browser_payload", raw);
    const resultText = await pyodide.runPythonAsync("browser_validate(browser_payload)");
    pyodide.globals.delete("browser_payload");

    const result = JSON.parse(resultText);
    lastReport = result.report;
    lastMarkdown = result.markdown;
    renderReport(lastReport);

    if (window.matchMedia("(max-width: 880px)").matches) {
      switchPanel("resultsPanel");
    }
  } catch (error) {
    console.error(error);
    showError(`Analysis failed: ${error.message || String(error)}`);
  } finally {
    if (pyodide) {
      try {
        pyodide.globals.delete("browser_payload");
      } catch (error) {
        console.debug("Temporary browser payload was already cleared.", error);
      }
    }
    setBusy(false);
  }
}

async function loadSample() {
  clearError();
  try {
    const response = await fetch("./sample_care_report.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const sample = await response.json();
    elements.manuscriptInput.value = JSON.stringify(sample, null, 2);
    setBusy(false);
  } catch (error) {
    showError(`Could not load the sample: ${error.message || String(error)}`);
  }
}

function resetResults() {
  lastReport = null;
  lastMarkdown = "";
  elements.emptyState.classList.remove("hidden");
  elements.resultsContent.classList.add("hidden");
  elements.exportActions.classList.add("hidden");
  elements.resultsTableBody.replaceChildren();
  elements.metricGrid.replaceChildren();
  elements.alertBox.classList.add("hidden");
  elements.resultSubtitle.textContent = "Run an analysis to see checklist coverage and item-level findings.";
}

function clearAll() {
  elements.manuscriptInput.value = "";
  elements.fileInput.value = "";
  clearError();
  resetResults();
  setBusy(false);
  elements.manuscriptInput.focus();
}

async function openFile(file) {
  clearError();
  if (!file) return;
  if (file.size > MAX_FILE_BYTES) {
    showError("File is larger than 2 MiB. Use a smaller text, Markdown, or JSON input.");
    elements.fileInput.value = "";
    return;
  }

  try {
    elements.manuscriptInput.value = await file.text();
    resetResults();
    setBusy(false);
  } catch (error) {
    showError(`Could not read the file: ${error.message || String(error)}`);
  }
}

function downloadText(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

elements.themeToggle.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  applyTheme(next);
  try {
    localStorage.setItem("care-review-theme", next);
  } catch (error) {
    console.warn("Theme preference could not be saved.", error);
  }
});

elements.manuscriptInput.addEventListener("input", () => setBusy(false));
elements.analyzeButton.addEventListener("click", analyze);
elements.loadSampleButton.addEventListener("click", loadSample);
elements.clearButton.addEventListener("click", clearAll);
elements.fileInput.addEventListener("change", (event) => openFile(event.target.files?.[0]));

elements.downloadJsonButton.addEventListener("click", () => {
  if (!lastReport) return;
  downloadText("care-checklist-report.json", JSON.stringify(lastReport, null, 2), "application/json");
});

elements.downloadMarkdownButton.addEventListener("click", () => {
  if (!lastMarkdown) return;
  downloadText("care-checklist-report.md", lastMarkdown, "text/markdown;charset=utf-8");
});

document.querySelectorAll(".tab-button").forEach((button) => {
  button.addEventListener("click", () => switchPanel(button.dataset.panel));
});

initializeTheme();
initializePython();
