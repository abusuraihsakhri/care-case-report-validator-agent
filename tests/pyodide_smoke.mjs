import { readFile } from "node:fs/promises";
import { loadPyodide } from "pyodide";

const pyodide = await loadPyodide();
const validatorSource = await readFile("care_validator.py", "utf8");

pyodide.FS.writeFile("care_validator.py", validatorSource);

const result = await pyodide.runPythonAsync(`
from care_validator import CARECaseReportValidator

validator = CARECaseReportValidator()
report = validator.validate({
    "title": "Example condition: A Case Report",
    "keywords": ["Example condition", "Case report"],
    "timeline": [
        {"relative_day": 0, "event": "Presentation"},
        {"relative_day": 1, "event": "Assessment"},
    ],
    "informed_consent": "Written informed consent was obtained for publication.",
})

assert report.items_total > 0
assert report.timeline_valid is True
(report.items_total, report.manuscript_title)
`);

if (!Array.isArray(result) && typeof result?.toJs === "function") {
  const converted = result.toJs();
  result.destroy?.();
  if (!converted || converted.length !== 2) {
    throw new Error("Unexpected Pyodide validator result.");
  }
} else if (!result) {
  throw new Error("Pyodide validator returned no result.");
}

console.log("Pyodide validator smoke test passed.");
