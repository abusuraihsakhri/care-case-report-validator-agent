# CARE Case Report Checklist Reviewer

Rule-based tools for reviewing case-report drafts against the **CARE 2013** reporting checklist. The repository provides a Python API, command-line interface, batch CSV workflow, and a browser interface that runs the same Python validator locally through Pyodide.

> **Scope:** the generated percentage and tier are repository-specific checklist-coverage heuristics. CARE does not define this scoring system. Results are not a clinical validation, publication-readiness decision, or privacy/de-identification certification.

## What it checks

- CARE 2013 checklist topics and sub-items, including title, keywords, abstract, patient information, clinical findings, timeline, diagnostic assessment, interventions, follow-up, discussion, patient perspective, and consent.
- Structured timeline order when relative-day values are supplied.
- A limited set of common direct-identifier patterns such as MRNs, SSNs, phone numbers, email addresses, and explicit dates of birth.
- JSON, Markdown/plain-text, and CSV batch inputs.
- JSON and Markdown report export.

The privacy pattern screen is intentionally limited. It does **not** implement all HIPAA Safe Harbor identifiers and must not be used as proof that text is de-identified.

## Browser application

GitHub Pages deployment is configured in `.github/workflows/pages.yml`. The page loads a pinned Pyodide runtime and executes `care_validator.py` in the browser.

The interface is light-themed by default, includes a dark-mode toggle, is responsive, and keeps the input and results workspace within the viewport with internal panel scrolling where needed.

### Browser privacy

Case-report text is processed in the browser and is not sent to this repository or to an application backend. The page stores only the selected color theme in `localStorage`. Loading the Python runtime requires a network request to the pinned Pyodide distribution on jsDelivr.

## Local use

Requirements: Python 3.10 or newer.

```bash
git clone https://github.com/abusuraihsakhri/care-case-report-validator-agent.git
cd care-case-report-validator-agent
python -m pip install -e .
```

Review the bundled structured example:

```bash
care-case-report-validator validate --file sample_care_report.json
```

Export JSON:

```bash
care-case-report-validator validate \
  --file sample_care_report.json \
  --format json \
  --output report.json
```

Export Markdown:

```bash
care-case-report-validator validate \
  --file sample_care_report.json \
  --format markdown \
  --output report.md
```

Run the bundled benchmark checks:

```bash
care-case-report-validator benchmark
```

Write a fresh copy of the bundled sample:

```bash
care-case-report-validator sample --output sample.json
```

Batch-process CSV records:

```bash
care-case-report-validator batch -i sample.csv -o care_audit_results.csv
```

The batch command does not infer consent when the input field is missing.

## Python API

```python
from care_validator import CARECaseReportValidator

validator = CARECaseReportValidator()
report = validator.validate({
    "title": "Example condition: A Case Report",
    "keywords": ["Example condition", "Case report"],
    "informed_consent": "Written informed consent was obtained for publication.",
})

print(report.overall_compliance_score)
print(report.items_met, report.items_partially_met, report.items_unmet)
```

Set `phi_strict=False` only when you intentionally want to disable the limited direct-identifier pattern screen.

## Testing

```bash
python -m pip install -e . pytest
python -m pip check
python -m compileall -q care_validator.py cli.py
python -m pytest -q
```

CI runs these checks on Python 3.10, 3.11, and 3.12 and also exercises the installed console command.

## Technology

- Python standard library only at runtime
- Pyodide 0.29.5 for browser-side Python execution
- Plain HTML, CSS, and JavaScript for the GitHub Pages interface
- GitHub Actions for CI and Pages deployment

Modern Chromium, Firefox, and Safari releases with WebAssembly support are expected to run the browser application. The initial Pyodide download is substantially larger than the application code and can be slower on constrained networks.

## CARE references

- Gagnier JJ, Kienle G, Altman DG, Moher D, Sox H, Riley D; CARE Group. *The CARE Guidelines: Consensus-based Clinical Case Reporting Guideline Development.* BMJ Case Rep. 2013. doi:10.1136/bcr-2013-201554.
- Riley DS, Barber MS, Kienle GS, et al. *CARE guidelines for case reports: explanation and elaboration document.* J Clin Epidemiol. 2017;89:218-235.
- CARE checklist: https://www.care-statement.org/checklist
- EQUATOR record: https://www.equator-network.org/reporting-guidelines/care/

## License

MIT. See [LICENSE](LICENSE).
