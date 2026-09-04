#!/usr/bin/env python3
"""
Unit Test Suite for CARE Case Report Validator Agent
====================================================
Comprehensive tests validating the 13-item CARE 2013 guideline compliance engine.
"""

import json
import unittest
from care_validator import (
    CARECaseReportValidator,
    CAREValidationReport,
    ComplianceStatus,
    ComplianceTier,
    AlertSeverity,
    PHISecurityAuditor,
    TimelineChronologyAuditor,
    format_markdown_report,
)
from cli import get_sample_compliant_report


class TestCAREValidator(unittest.TestCase):

    def setUp(self):
        self.validator = CARECaseReportValidator()
        self.sample_report = get_sample_compliant_report()

    # 1. Standard Reference Cases
    def test_fully_compliant_report_scores_high(self):
        report = self.validator.validate(self.sample_report)
        self.assertGreaterEqual(report.overall_compliance_score, 90.0)
        self.assertEqual(report.compliance_tier, ComplianceTier.FULLY_COMPLIANT)
        self.assertEqual(report.items_unmet, 0)
        self.assertTrue(report.timeline_valid)

    def test_completely_empty_payload(self):
        report = self.validator.validate({})
        self.assertLess(report.overall_compliance_score, 30.0)
        self.assertEqual(report.compliance_tier, ComplianceTier.NON_COMPLIANT)
        self.assertGreater(report.items_unmet, 10)

    # 2. Section 1 - Title
    def test_title_with_case_report_and_topic(self):
        data = {"title": "Successful Management of Rare Autoimmune Hepatitis: A Case Report"}
        report = self.validator.validate(data)
        item1 = next(it for it in report.item_evaluations if it.item_id == "1")
        self.assertEqual(item1.status, ComplianceStatus.MET)
        self.assertEqual(item1.score, 1.0)

    def test_title_without_case_report_phrase(self):
        data = {"title": "A Rare Presentation of Autoimmune Hepatitis in a Teenager"}
        report = self.validator.validate(data)
        item1 = next(it for it in report.item_evaluations if it.item_id == "1")
        self.assertEqual(item1.status, ComplianceStatus.PARTIALLY_MET)
        self.assertLess(item1.score, 1.0)

    def test_missing_title(self):
        data = {"title": ""}
        report = self.validator.validate(data)
        item1 = next(it for it in report.item_evaluations if it.item_id == "1")
        self.assertEqual(item1.status, ComplianceStatus.UNMET)
        self.assertEqual(item1.score, 0.0)

    # 3. Section 2 - Keywords
    def test_keywords_valid_range(self):
        data = {"keywords": ["Hepatitis", "Immunology", "Prednisone"]}
        report = self.validator.validate(data)
        item2 = next(it for it in report.item_evaluations if it.item_id == "2")
        self.assertEqual(item2.status, ComplianceStatus.MET)
        self.assertEqual(item2.score, 1.0)

    def test_keywords_single_keyword(self):
        data = {"keywords": ["Hepatitis"]}
        report = self.validator.validate(data)
        item2 = next(it for it in report.item_evaluations if it.item_id == "2")
        self.assertEqual(item2.status, ComplianceStatus.PARTIALLY_MET)

    def test_keywords_comma_separated_string(self):
        data = {"keywords": "Liver, Jaundice, Biopsy, Steroids"}
        report = self.validator.validate(data)
        item2 = next(it for it in report.item_evaluations if it.item_id == "2")
        self.assertEqual(item2.status, ComplianceStatus.MET)

    def test_keywords_missing(self):
        data = {"keywords": []}
        report = self.validator.validate(data)
        item2 = next(it for it in report.item_evaluations if it.item_id == "2")
        self.assertEqual(item2.status, ComplianceStatus.UNMET)

    # 4. Section 3 - Abstract Sub-items
    def test_abstract_subitems_presence(self):
        data = {
            "abstract": {
                "introduction": "This is a unique case of refractory encephalitis.",
                "symptoms": "Patient presented with acute behavioral disturbance and seizures.",
                "diagnoses_interventions_outcomes": "Diagnosed via CSF antibody panel; treated with IVIG.",
                "conclusion": "Early immunotherapy is critical in pediatric presentations.",
            }
        }
        report = self.validator.validate(data)
        abs_items = [it for it in report.item_evaluations if it.item_id in ["3a", "3b", "3c", "3d"]]
        for it in abs_items:
            self.assertEqual(it.status, ComplianceStatus.MET)

    def test_abstract_partial_subitems(self):
        data = {
            "abstract": {
                "introduction": "Short note",
            }
        }
        report = self.validator.validate(data)
        item3a = next(it for it in report.item_evaluations if it.item_id == "3a")
        item3b = next(it for it in report.item_evaluations if it.item_id == "3b")
        self.assertEqual(item3a.status, ComplianceStatus.PARTIALLY_MET)
        self.assertEqual(item3b.status, ComplianceStatus.UNMET)

    # 5. Section 5 - Patient Demographics & History
    def test_patient_demographics_complete(self):
        data = {
            "patient_information": {
                "age": 42,
                "sex": "Male",
                "ethnicity": "Asian",
                "chief_complaint": "Severe right upper quadrant pain.",
                "history": "History of hypertension and dyslipidemia.",
            }
        }
        report = self.validator.validate(data)
        item5a = next(it for it in report.item_evaluations if it.item_id == "5a")
        item5b = next(it for it in report.item_evaluations if it.item_id == "5b")
        item5c = next(it for it in report.item_evaluations if it.item_id == "5c")
        self.assertEqual(item5a.status, ComplianceStatus.MET)
        self.assertEqual(item5b.status, ComplianceStatus.MET)
        self.assertEqual(item5c.status, ComplianceStatus.MET)

    def test_patient_demographics_partial(self):
        data = {
            "patient_information": {
                "age": 42,
            }
        }
        report = self.validator.validate(data)
        item5a = next(it for it in report.item_evaluations if it.item_id == "5a")
        self.assertEqual(item5a.status, ComplianceStatus.PARTIALLY_MET)

    # 6. Section 7 - Timeline & Chronology
    def test_timeline_chronological_ordering(self):
        data = {
            "timeline": [
                {"relative_day": 1, "event": "Symptom onset"},
                {"relative_day": 3, "event": "Hospital admission"},
                {"relative_day": 10, "event": "Discharge"},
            ]
        }
        report = self.validator.validate(data)
        self.assertTrue(report.timeline_valid)
        item7 = next(it for it in report.item_evaluations if it.item_id == "7")
        self.assertEqual(item7.status, ComplianceStatus.MET)

    def test_timeline_inversion_detection(self):
        data = {
            "timeline": [
                {"relative_day": 5, "event": "Hospital admission"},
                {"relative_day": 2, "event": "Symptom onset"},  # Inversion!
            ]
        }
        report = self.validator.validate(data)
        self.assertFalse(report.timeline_valid)
        inversion_alerts = [a for a in report.alerts if a.category == "CHRONOLOGY_INVERSION"]
        self.assertGreater(len(inversion_alerts), 0)

    def test_timeline_sparse_entries(self):
        data = {
            "timeline": [
                {"relative_day": 1, "event": "Single event"},
            ]
        }
        report = self.validator.validate(data)
        self.assertFalse(report.timeline_valid)

    # 7. HIPAA / PHI Direct Identifiers Auditing
    def test_phi_ssn_detection(self):
        alerts = PHISecurityAuditor.audit_text("Patient SSN is 000-12-3456.")
        self.assertEqual(len(alerts), 1)
        self.assertIn("Social Security Number", alerts[0].message)

    def test_phi_mrn_detection(self):
        alerts = PHISecurityAuditor.audit_text("Admitted under MRN: 12345678 to ward 4.")
        self.assertEqual(len(alerts), 1)
        self.assertIn("Medical Record Number", alerts[0].message)

    def test_phi_email_and_phone_detection(self):
        alerts = PHISecurityAuditor.audit_text("Contact: doctor@hospital.org or 555-123-4567.")
        self.assertEqual(len(alerts), 2)

    def test_clean_text_no_phi_alerts(self):
        alerts = PHISecurityAuditor.audit_text("A 55-year-old female presented with abdominal pain.")
        self.assertEqual(len(alerts), 0)

    # 8. Section 8 - Diagnostic Assessment & Challenges
    def test_diagnostic_assessment_full(self):
        data = {
            "diagnostic_assessment": {
                "diagnostic_methods": "CT scan revealed a 4cm adrenal mass. Biopsy confirmed pheochromocytoma.",
                "challenges": "Hypertensive crisis during imaging delayed tissue biopsy.",
                "differential_diagnosis": "Differential included renal cell carcinoma and adrenal adenoma.",
                "prognosis": "Benign histology with 5-year disease-free survival expectation.",
            }
        }
        report = self.validator.validate(data)
        for item_id in ["8a", "8b", "8c", "8d"]:
            item = next(it for it in report.item_evaluations if it.item_id == item_id)
            self.assertEqual(item.status, ComplianceStatus.MET)

    # 9. Section 9 & 10 - Therapeutic Intervention & Outcomes
    def test_therapeutic_intervention_and_adherence(self):
        data = {
            "therapeutic_intervention": {
                "treatment": "Surgical resection via laparoscopic adrenalectomy.",
                "administration": "Phenoxybenzamine 10mg TID for 14 days preoperatively.",
            },
            "follow_up_and_outcomes": {
                "outcomes": "Blood pressure normalized completely post-resection.",
                "adherence": "100% adherence to preoperative alpha-blockade protocol.",
                "adverse_events": "No perioperative complications observed.",
            }
        }
        report = self.validator.validate(data)
        for item_id in ["9a", "9b", "10a", "10c", "10d"]:
            item = next(it for it in report.item_evaluations if it.item_id == item_id)
            self.assertEqual(item.status, ComplianceStatus.MET)

    # 10. Section 13 - Informed Consent & Ethics
    def test_informed_consent_documentation(self):
        data = {"informed_consent": "Written informed consent was obtained from the patient for publication."}
        report = self.validator.validate(data)
        item13 = next(it for it in report.item_evaluations if it.item_id == "13")
        self.assertEqual(item13.status, ComplianceStatus.MET)

    def test_missing_informed_consent(self):
        data = {"informed_consent": ""}
        report = self.validator.validate(data)
        item13 = next(it for it in report.item_evaluations if it.item_id == "13")
        self.assertEqual(item13.status, ComplianceStatus.UNMET)

    # 11. Plain Text / Markdown Parsing
    def test_markdown_manuscript_parsing(self):
        md_text = """
# Rare Presentation of Takotsubo Cardiomyopathy: A Case Report
Keywords: Takotsubo, Cardiomyopathy, Echocardiography

## Abstract
A 68-year-old woman presented with apical ballooning after emotional stress. Treated with ACE inhibitors with recovery.

## Introduction
Takotsubo cardiomyopathy mimics acute coronary syndrome.

## Patient Information
A 68-year-old female presented with substernal chest pressure following acute bereavement.

## Clinical Findings
Blood pressure 110/70, heart rate 95 bpm. S3 gallop audible.

## Timeline
Day 1: Acute chest pain; Day 2: Coronary angiogram clean; Day 14: Follow-up echo normal.

## Diagnostic Assessment
Coronary angiography showed unobstructed coronaries. Ventriculography showed apical ballooning.

## Therapeutic Intervention
Lisinopril 5 mg daily and Metoprolol succinate 25 mg daily.

## Follow-up and Outcomes
Ejection fraction improved from 35% to 60% at 4 weeks. No adverse drug reactions.

## Discussion
This case demonstrates reversible ventricular dysfunction. Clinicians must rule out STEMI first.

## Informed Consent
Written informed consent was obtained from the patient.
"""
        report = self.validator.validate(md_text)
        self.assertGreaterEqual(report.overall_compliance_score, 75.0)
        self.assertEqual(report.manuscript_title, "Rare Presentation of Takotsubo Cardiomyopathy: A Case Report")

    # 12. Serialization & Formatting
    def test_report_dict_serialization(self):
        report = self.validator.validate(self.sample_report)
        d = report.to_dict()
        self.assertIsInstance(d, dict)
        self.assertIn("overall_compliance_score", d)
        self.assertIn("item_evaluations", d)
        self.assertEqual(len(d["item_evaluations"]), report.items_total)

    def test_markdown_report_formatting(self):
        report = self.validator.validate(self.sample_report)
        md = format_markdown_report(report)
        self.assertIn("# CARE Case Report Validation Audit", md)
        self.assertIn("Overall Compliance Score", md)
        self.assertIn("CARE 2013 Item-by-Item Checklist Breakdown", md)

    def test_invalid_payload_type(self):
        with self.assertRaises(ValueError):
            self.validator.validate(12345)  # type: ignore


if __name__ == "__main__":
    unittest.main()
