# CARE Case Report Validator Agent

An automated clinical compliance auditor and multi-agent validation engine for medical case report manuscripts adhering to the **13-Item CARE 2013 Guidelines** (*Consensus-based Clinical Case Reporting Guideline Development*).

---

## Clinical Domain & Background

The **CARE Guidelines** (Gagnier et al., 2013; Riley et al., 2017) provide a consensus-based framework to improve the transparency, completeness, and clinical utility of published case reports. Biomedical journals require authors to verify that case reports adhere to all 13 core sections to ensure diagnostic clarity, therapeutic transparency, and patient confidentiality.

This agent evaluates structured case data or raw clinical manuscripts, auditing:
1. **Manuscript Completeness**: Evaluates all 13 CARE checklist items (30 distinct sub-items).
2. **HIPAA Safe Harbor & Privacy Compliance**: Scans for 18 direct Protected Health Information (PHI) identifiers including SSN, MRN, phone numbers, and un-anonymized names.
3. **Timeline Chronology & Consistency**: Validates chronological milestone progression and flags date inversions or sparse timelines.
4. **Therapeutic & Diagnostic Reasoning**: Checks that diagnostic assessments and interventions contain explicit dosages, routes, rationales, and adverse event reporting.

---

## CARE 2013 Checklist Item Architecture

| Item | Section | Description & Standard Checklist Criteria |
| :--- | :--- | :--- |
| **1** | Title | Contains 'Case Report' / 'Case Study' and identifies phenomenon/diagnosis of interest |
| **2** | Keywords | 2 to 5 relevant MeSH keywords identifying diagnoses, interventions, or features |
| **3a-d** | Abstract | Structured summary: Introduction/Uniqueness, Symptoms, Diagnoses/Interventions/Outcomes, Conclusion |
| **4** | Introduction | Brief clinical context, literature background, and rationale for case reporting |
| **5a-d** | Patient Information | De-identified demographics (Age, Sex, Ethnicity), Chief Complaint, Medical/Family History, Past Interventions |
| **6** | Clinical Findings | Physical examination findings, vital signs, and relevant systemic signs |
| **7** | Timeline | Chronological milestone ordering (symptom onset, admission, diagnosis, interventions, follow-up) |
| **8a-d** | Diagnostic Assessment | Diagnostic testing methods (labs/imaging), challenges/delays, differential diagnoses, prognostic staging |
| **9a-c** | Therapeutic Intervention | Types of intervention (pharmacologic/surgical), administration (dosage/route/duration), changes with rationale |
| **10a-d** | Follow-up & Outcomes | Clinician/patient-assessed outcomes, follow-up tests, treatment adherence/tolerability, adverse event documentation |
| **11a-d** | Discussion | Strengths/limitations of management, literature review, scientific rationale, primary take-away lessons |
| **12** | Patient Perspective | Patient's personal narrative, experience, or reflection on care |
| **13** | Informed Consent | Explicit documentation of patient informed consent or institutional ethics approval |

---

## Compliance Tiers & Scoring Logic

The validator computes an overall weighted compliance score ($S_{CARE} \in [0, 100\%]$):

$$S_{CARE} = \frac{\sum_{i=1}^{N} w_i \cdot s_i}{\sum_{i=1}^{N} w_i} \times 100\%$$

Where:
- $s_i \in [0.0, 1.0]$: Item compliance score (1.0 = MET, 0.5-0.8 = PARTIALLY_MET, 0.0 = UNMET).
- $w_i$: Item weight based on clinical critical importance.

### Tier Classification
- **`FULLY_COMPLIANT`**: Score $\ge 90\%$ (Ready for journal submission).
- **`SUBSTANTIALLY_COMPLIANT`**: $75\% \le \text{Score} < 90\%$ (Minor revisions required).
- **`MODERATELY_COMPLIANT`**: $50\% \le \text{Score} < 75\%$ (Substantial gaps in clinical documentation).
- **`NON_COMPLIANT`**: Score $< 50\%$ (Incomplete manuscript).

---

## Installation & Requirements

Pure Python 3.9+ with zero external dependencies.

```bash
# Clone and enter directory
cd care-case-report-validator-agent
```

---

## CLI Usage

### 1. Validate a JSON Case Report Payload
```bash
python cli.py validate --file sample_care_report.json
```

### 2. Validate a Markdown Manuscript File
```bash
python cli.py validate --file manuscript.md --format markdown --output audit_report.md
```

### 3. Output Pure Machine-Readable JSON
```bash
python cli.py validate --file sample_care_report.json --json
```

### 4. Interactive Manuscript Audit Wizard
```bash
python cli.py interactive
```

### 5. Run Verification Benchmark Suite
```bash
python cli.py benchmark
```

### 6. Export Starter JSON Template
```bash
python cli.py sample -o template_report.json
```

---

## Python API Usage

```python
from care_validator import CARECaseReportValidator

validator = CARECaseReportValidator()

payload = {
    "title": "Unusual Presentation of Autoimmune Hepatitis: A Case Report",
    "keywords": ["Autoimmune hepatitis", "Jaundice", "Azathioprine"],
    "abstract": {
        "introduction": "Autoimmune hepatitis presenting with hyperacute liver failure.",
        "symptoms": "Jaundice and encephalopathy.",
        "diagnoses_interventions_outcomes": "Liver biopsy showed interface hepatitis; treated with corticosteroids.",
        "conclusion": "Early biopsy avoids unnecessary liver transplantation."
    },
    "patient_information": {
        "age": 34,
        "sex": "Female",
        "chief_complaint": "Acute jaundice and pruritus",
        "history": "No prior liver disease, non-drinker."
    },
    "timeline": [
        {"relative_day": 1, "event": "Symptom onset with scleral icterus"},
        {"relative_day": 4, "event": "Hospital admission and liver biopsy"},
        {"relative_day": 5, "event": "Initiated Prednisone 40mg daily"}
    ],
    "informed_consent": "Written informed consent was obtained from the patient."
}

report = validator.validate(payload)
print(f"Score: {report.overall_compliance_score:.1f}% ({report.compliance_tier.value})")
print(f"Items Met: {report.items_met}/{report.items_total}")
```

---

## Testing & Quality Assurance

Run the exhaustive test suite:

```bash
python -m unittest -v test_care_validator.py
```

Test coverage includes:
- Gold-standard reference case reports.
- Item-by-item granular tests across all 13 CARE sections.
- PHI / HIPAA direct identifier detection (SSN, MRN, phone, email, names).
- Timeline chronology monotonicity and inversion alerts.
- Raw text and Markdown manuscript parsing.
- Report serialization (JSON, Markdown, Dictionary).

---

## References

1. **Gagnier JJ, Kienle G, Altman DG, Moher D, Sox H, Riley D; CARE Group.** The CARE guidelines: consensus-based clinical case report guideline development. *BMJ Case Reports*. 2013;2013:bcr2013201554.
2. **Riley DS, Barber MS, Kienle GS, et al.** CARE guidelines for case reports: explanation and elaboration document. *Journal of Clinical Epidemiology*. 2017;89:218-235.

---

## License

MIT License.
