# CARE 2013 Case Report Completeness & Manuscript Auditor

A clinically validated, pure Python manuscript validation engine implementing the **Consensus-based Clinical Case Reporting Guideline Development (CARE 2013)** 13-item checklist, EQUATOR Network reporting standards, timeline chronology auditing, and automated Protected Health Information (Zero-PHI) compliance verification.

---

## The CARE 2013 13-Item Guideline Architecture

The CARE guidelines (Gagnier et al., *BMJ Case Rep* 2013; Riley et al., *J Clin Epidemiol* 2017) provide a standardized 13-item framework for transparent and complete reporting of medical case reports.

### Checklist Item Taxonomy

| Item | CARE Domain | Key Reporting Criteria |
|:---|:---|:---|
| **1** | **Title** | The words "case report" should be in the title along with the area of focus / diagnosis. |
| **2** | **Key Words** | 2 to 5 key words identifying diagnoses or interventions. |
| **3a–d** | **Abstract** | Structured abstract: (a) Introduction, (b) Symptoms/findings, (c) Diagnoses & interventions, (d) Main conclusion. |
| **4** | **Introduction** | Brief background context referencing relevant medical literature. |
| **5a–d** | **Patient Information** | (a) De-identified demographic information, (b) Symptoms/complaints, (c) Medical/family history, (d) Past interventions. |
| **6** | **Clinical Findings** | Physical examination findings and critical vital signs. |
| **7** | **Timeline** | Historical and current milestones in the patient episode organized chronologically. |
| **8a–d** | **Diagnostic Assessment** | (a) Diagnostic methods (imaging, pathology), (b) Diagnostic challenges, (c) Diagnostic reasoning / differentials, (d) Prognosis. |
| **9a–c** | **Therapeutic Intervention** | (a) Interventions (pharmacological, surgical), (b) Administration/dosages, (c) Changes in therapeutic strategy. |
| **10a–d**| **Follow-up & Outcomes** | (a) Clinician and patient-assessed outcomes, (b) Follow-up testing, (c) Treatment adherence, (d) Adverse events. |
| **11a–d**| **Discussion** | (a) Strengths and limitations, (b) Discussion of relevant literature, (c) Rationale for conclusions, (d) Take-away lessons. |
| **12** | **Patient Perspective** | Patient / guardian shared perspective or experience where possible. |
| **13** | **Informed Consent** | Explicit statement verifying informed consent for publication was obtained. |

---

### Compliance Scoring & Tiers

$$\text{Section Score} = \frac{\sum \text{Item Scores}}{\text{Number of Items in Section}} \times 100\%$$
$$\text{Overall Compliance Score} = \frac{\sum_{i=1}^{N} \text{Score}_i}{N} \times 100\%$$

- **Fully Compliant ($\ge 90\%$):** Manuscript fulfills all primary checklist items; publication-ready.
- **Substantially Compliant ($75\% - 89\%$):** Minor omissions; easily remediated with structured additions.
- **Moderately Compliant ($50\% - 74\%$):** Missing key components (e.g., timeline, adverse events, or differential reasoning).
- **Non-Compliant ($< 50\%$):** Critical deficiencies requiring extensive manuscript restructuring.

---

## Features

- **Full CARE 2013 Item Evaluation:** Audits all 13 checklist domains with item-by-item granular scoring.
- **Automated Zero-PHI Inspection:** Scans text for exposed MRNs, SSNs, phone numbers, and direct patient identifiers.
- **Timeline Chronology Auditor:** Validates sequence and temporal coherence of intervention milestones.
- **Batch CSV & Multi-format Export:** Batch triage of case reports from CSV or JSON with Markdown report generation.
- **Zero Runtime Dependencies:** Pure Python implementation relying strictly on the Python Standard Library.

---

## Installation & Requirements

- Python 3.10+ (tested on 3.10, 3.11, 3.12)
- Zero external runtime dependencies.

```bash
git clone https://github.com/abusuraihsakhri/care-case-report-validator-agent.git
cd care-case-report-validator-agent
```

---

## CLI Usage

### 1. Validate a Case Report JSON File
```bash
python cli.py validate --file sample_care_report.json
```

### 2. Export Validation Report to Markdown
```bash
python cli.py validate --file sample_care_report.json --format markdown --output audit_report.md
```

### 3. Batch Audit Case Reports from CSV
```bash
python cli.py batch -i sample.csv -o care_audit_results.csv
```

### 4. Run Built-in Verification Benchmarks
```bash
python cli.py benchmark
```

---

## Python API Quickstart

```python
from care_validator import CARECaseReportValidator
from cli import get_sample_compliant_report

validator = CARECaseReportValidator()
case_data = get_sample_compliant_report()

report = validator.validate(case_data)
print(f"Compliance Score: {report.overall_compliance_score:.1f}%")
print(f"Compliance Tier: {report.compliance_tier.value}")
print(f"Items Met: {report.items_met}/{report.items_total}")
print(f"Timeline Valid: {report.timeline_valid}")
```

---

## Testing & Verification

Run the test suite:

```bash
python -m pytest -p no:zarr
```

