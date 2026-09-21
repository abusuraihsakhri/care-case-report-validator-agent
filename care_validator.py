#!/usr/bin/env python3
"""
CARE 2013 case-report checklist reviewer.

This module applies deterministic, rule-based checks to structured data or
plain-text drafts. The numeric score and tier are repository-specific
heuristics for checklist coverage; they are not part of the CARE guideline and
must not be interpreted as clinical validation, publication readiness, or a
formal privacy/de-identification determination.

References:
- Gagnier JJ, Kienle G, Altman DG, Moher D, Sox H, Riley D; CARE Group.
  The CARE guidelines: consensus-based clinical case report guideline development.
  BMJ Case Rep. 2013;2013:bcr2013201554.
- Riley DS, Barber MS, Kienle GS, et al. CARE guidelines for case reports:
  explanation and elaboration document. J Clin Epidemiol. 2017;89:218-235.

License: MIT
"""

from __future__ import annotations

import csv
import datetime
import json
import re
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


# ==============================================================================
# DOMAIN ENUMS & DATA STRUCTURES
# ==============================================================================

class ComplianceStatus(str, Enum):
    MET = "MET"
    PARTIALLY_MET = "PARTIALLY_MET"
    UNMET = "UNMET"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ComplianceTier(str, Enum):
    """Backward-compatible labels for repository-specific heuristic score bands."""

    FULLY_COMPLIANT = "FULLY_COMPLIANT"             # >= 90%
    SUBSTANTIALLY_COMPLIANT = "SUBSTANTIALLY_COMPLIANT" # 75% - 89%
    MODERATELY_COMPLIANT = "MODERATELY_COMPLIANT"     # 50% - 74%
    NON_COMPLIANT = "NON_COMPLIANT"                 # < 50%


class AlertSeverity(str, Enum):
    INFO = "INFO"
    ADVISORY = "ADVISORY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class ItemEvaluation:
    """Evaluation result for a specific CARE checklist item."""
    item_id: str
    section: str
    title: str
    status: ComplianceStatus
    score: float  # 0.0 to 1.0
    weight: float
    findings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "section": self.section,
            "title": self.title,
            "status": self.status.value,
            "score": round(self.score, 3),
            "weight": self.weight,
            "findings": self.findings,
            "recommendations": self.recommendations,
        }


@dataclass
class AuditAlert:
    """Specific finding or warning generated during audit."""
    severity: AlertSeverity
    category: str
    message: str
    field_name: Optional[str] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "category": self.category,
            "message": self.message,
            "field_name": self.field_name,
            "suggestion": self.suggestion,
        }


@dataclass
class TimelineMilestone:
    """Chronological milestone in patient trajectory."""
    time_point: str
    event: str
    parsed_date: Optional[str] = None
    relative_day: Optional[int] = None
    intervention_or_outcome: Optional[str] = None


@dataclass
class CAREValidationReport:
    """Comprehensive validation report for a case report manuscript."""
    manuscript_title: str
    timestamp: str
    overall_compliance_score: float  # 0.0 - 100.0%
    compliance_tier: ComplianceTier
    items_total: int
    items_met: int
    items_partially_met: int
    items_unmet: int
    section_scores: Dict[str, float]
    item_evaluations: List[ItemEvaluation]
    alerts: List[AuditAlert]
    phi_violations: List[str]
    timeline_valid: bool
    summary_strengths: List[str]
    summary_deficiencies: List[str]
    actionable_checklist: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manuscript_title": self.manuscript_title,
            "timestamp": self.timestamp,
            "overall_compliance_score": round(self.overall_compliance_score, 1),
            "compliance_tier": self.compliance_tier.value,
            "items_total": self.items_total,
            "items_met": self.items_met,
            "items_partially_met": self.items_partially_met,
            "items_unmet": self.items_unmet,
            "section_scores": {k: round(v, 1) for k, v in self.section_scores.items()},
            "item_evaluations": [item.to_dict() for item in self.item_evaluations],
            "alerts": [alert.to_dict() for alert in self.alerts],
            "phi_violations": self.phi_violations,
            "timeline_valid": self.timeline_valid,
            "summary_strengths": self.summary_strengths,
            "summary_deficiencies": self.summary_deficiencies,
            "actionable_checklist": self.actionable_checklist,
        }


# ==============================================================================
# CARE CHECKLIST SPECIFICATION (2013 STANDARD)
# ==============================================================================

CARE_CHECKLIST_SPEC: List[Dict[str, Any]] = [
    {
        "item_id": "1",
        "section": "Title",
        "title": "Title contains 'case report' and identifies phenomenon of interest",
        "weight": 1.0,
        "description": "The words 'case report' or 'case study' should be in the title along with the area of focus."
    },
    {
        "item_id": "2",
        "section": "Keywords",
        "title": "Key Words (2 to 5 words)",
        "weight": 1.0,
        "description": "Two to five key words that identify diagnoses or interventions, including 'case report'."
    },
    {
        "item_id": "3a",
        "section": "Abstract",
        "title": "Abstract: Introduction / Uniqueness",
        "weight": 1.0,
        "description": "What is unique about this case and what does it add to the literature?"
    },
    {
        "item_id": "3b",
        "section": "Abstract",
        "title": "Abstract: Main Symptoms and Findings",
        "weight": 1.0,
        "description": "The patient's main symptoms and important clinical findings."
    },
    {
        "item_id": "3c",
        "section": "Abstract",
        "title": "Abstract: Diagnoses, Interventions, Outcomes",
        "weight": 1.0,
        "description": "The main diagnoses, therapeutic interventions, and clinical outcomes."
    },
    {
        "item_id": "3d",
        "section": "Abstract",
        "title": "Abstract: Conclusion and Take-away Lessons",
        "weight": 1.0,
        "description": "The primary take-away lesson or clinical implication."
    },
    {
        "item_id": "4",
        "section": "Introduction",
        "title": "Introduction: Background and Context",
        "weight": 1.5,
        "description": "Brief summary of the background and context of this case with relevant literature citations."
    },
    {
        "item_id": "5a",
        "section": "Patient Information",
        "title": "Patient Demographics and De-identification",
        "weight": 1.5,
        "description": "De-identified demographic and patient-specific information (age, sex, ethnicity, occupation)."
    },
    {
        "item_id": "5b",
        "section": "Patient Information",
        "title": "Chief Complaint & Presenting Symptoms",
        "weight": 1.5,
        "description": "The primary symptoms and chief complaint presenting to medical care."
    },
    {
        "item_id": "5c",
        "section": "Patient Information",
        "title": "Medical, Family, and Psychosocial History",
        "weight": 1.5,
        "description": "Relevant past medical, family, and psychosocial history including genetic information and comorbidities."
    },
    {
        "item_id": "5d",
        "section": "Patient Information",
        "title": "Relevant Past Interventions and Outcomes",
        "weight": 1.0,
        "description": "Relevant past interventions and their outcomes."
    },
    {
        "item_id": "6",
        "section": "Clinical Findings",
        "title": "Physical Examination and Clinical Findings",
        "weight": 1.5,
        "description": "Relevant physical examination (PE) findings and other clinical observations."
    },
    {
        "item_id": "7",
        "section": "Timeline",
        "title": "Timeline of Events / Milestones",
        "weight": 2.0,
        "description": "Chronological table, figure, or sequential narrative detailing milestones."
    },
    {
        "item_id": "8a",
        "section": "Diagnostic Assessment",
        "title": "Diagnostic Methods (Labs, Imaging, Surveys)",
        "weight": 1.5,
        "description": "Diagnostic testing methods including laboratory, imaging, and histology results."
    },
    {
        "item_id": "8b",
        "section": "Diagnostic Assessment",
        "title": "Diagnostic Challenges and Difficulties",
        "weight": 1.0,
        "description": "Diagnostic challenges (e.g. diagnostic uncertainty, delays, atypical presentation)."
    },
    {
        "item_id": "8c",
        "section": "Diagnostic Assessment",
        "title": "Diagnostic Reasoning and Differential Diagnoses",
        "weight": 1.5,
        "description": "Diagnostic reasoning including other diagnoses considered and ruling-out rationale."
    },
    {
        "item_id": "8d",
        "section": "Diagnostic Assessment",
        "title": "Prognostic Characteristics / Staging",
        "weight": 1.0,
        "description": "Prognostic characteristics (e.g. disease staging) where applicable."
    },
    {
        "item_id": "9a",
        "section": "Therapeutic Intervention",
        "title": "Types of Therapeutic Intervention",
        "weight": 1.5,
        "description": "Types of therapeutic intervention (pharmacologic, surgical, preventive, self-care)."
    },
    {
        "item_id": "9b",
        "section": "Therapeutic Intervention",
        "title": "Administration of Intervention (Dosage, Route, Duration)",
        "weight": 1.5,
        "description": "Dosage, strength, duration, and frequency of therapeutic administration."
    },
    {
        "item_id": "9c",
        "section": "Therapeutic Intervention",
        "title": "Changes in Therapeutic Intervention with Rationale",
        "weight": 1.0,
        "description": "Changes in interventions and explanation for the adjustments."
    },
    {
        "item_id": "10a",
        "section": "Follow-up and Outcomes",
        "title": "Clinician and Patient-Assessed Outcomes",
        "weight": 1.5,
        "description": "Clinical follow-up assessments and patient-reported outcome measures."
    },
    {
        "item_id": "10b",
        "section": "Follow-up and Outcomes",
        "title": "Follow-up Diagnostic Test Results",
        "weight": 1.0,
        "description": "Follow-up diagnostic testing results demonstrating resolution or progression."
    },
    {
        "item_id": "10c",
        "section": "Follow-up and Outcomes",
        "title": "Intervention Adherence and Tolerability",
        "weight": 1.5,
        "description": "Assessment of patient adherence, tolerance, and treatment compliance."
    },
    {
        "item_id": "10d",
        "section": "Follow-up and Outcomes",
        "title": "Adverse and Unanticipated Events",
        "weight": 1.5,
        "description": "Explicit reporting of adverse drug reactions or unanticipated clinical events (or explicit statement of none)."
    },
    {
        "item_id": "11a",
        "section": "Discussion",
        "title": "Discussion: Strengths and Limitations",
        "weight": 1.5,
        "description": "Strengths and limitations in your management and approach to this case."
    },
    {
        "item_id": "11b",
        "section": "Discussion",
        "title": "Discussion: Relevant Literature Context",
        "weight": 1.5,
        "description": "Discussion of relevant medical literature and comparative analysis."
    },
    {
        "item_id": "11c",
        "section": "Discussion",
        "title": "Discussion: Scientific Rationale for Conclusions",
        "weight": 1.5,
        "description": "Scientific justification and mechanistic rationale for clinical conclusions."
    },
    {
        "item_id": "11d",
        "section": "Discussion",
        "title": "Discussion: Primary Take-away Lessons",
        "weight": 1.5,
        "description": "Clear, actionable take-away lessons / learning points for practitioners."
    },
    {
        "item_id": "12",
        "section": "Patient Perspective",
        "title": "Patient Perspective or Experience",
        "weight": 1.0,
        "description": "Patient shared perspective, reflection, or narrative about their illness journey."
    },
    {
        "item_id": "13",
        "section": "Informed Consent",
        "title": "Informed Consent & Ethics Statement",
        "weight": 2.0,
        "description": "Informed consent obtained from the patient/guardian or institutional ethics approval statement."
    },
]


# ==============================================================================
# AUDIT SUB-AGENTS & RULE ENGINES
# ==============================================================================

class PHISecurityAuditor:
    """Screens for a limited set of common direct-identifier patterns.

    This is a conservative pattern screen, not a complete HIPAA Safe Harbor
    implementation and not a de-identification certification.
    """

    PHI_PATTERNS = [
        (r"\b\d{3}-\d{2}-\d{4}\b", "Social Security Number (SSN)", False),
        (r"\bMRN\s*[:#]?\s*\d+\b", "Medical Record Number (MRN)", True),
        (r"\b(?:patient(?:'s)?|pt|subject)\s+(?:name\s+is|named|is\s+named)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", "Direct Patient Full Name", False),
        (r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b", "Phone Number", False),
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "Email Address", True),
        (r"\b(?:DOB|Date of Birth)\s*[:=]?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", "Exact Date of Birth", True),
    ]

    @classmethod
    def audit_text(cls, text: str) -> List[AuditAlert]:
        alerts = []
        for pattern, desc, ignore_case in cls.PHI_PATTERNS:
            flags = re.IGNORECASE if ignore_case else 0
            matches = re.findall(pattern, text, flags)
            if matches:
                alerts.append(
                    AuditAlert(
                        severity=AlertSeverity.CRITICAL,
                        category="HIPAA_PHI_VIOLATION",
                        message=f"Potential protected health information detected: {desc} ({len(matches)} occurrence(s)).",
                        field_name="manuscript_body",
                        suggestion="Review and remove or de-identify direct identifiers as appropriate. This pattern screen is not a HIPAA de-identification determination."
                    )
                )
        return alerts


class TimelineChronologyAuditor:
    """Validates chronological consistency of clinical milestones."""

    @staticmethod
    def evaluate_timeline(timeline_data: Any) -> Tuple[bool, List[str], List[AuditAlert]]:
        alerts = []
        findings = []
        is_valid = True

        if not timeline_data:
            return False, ["No structured or narrative timeline provided."], [
                AuditAlert(
                    severity=AlertSeverity.WARNING,
                    category="TIMELINE_MISSING",
                    message="Case report lacks chronological timeline or milestone summary.",
                    field_name="timeline",
                    suggestion="Add a chronological table or figure detailing onset, evaluation, treatment, and follow-up milestones (CARE item 7)."
                )
            ]

        if isinstance(timeline_data, list):
            # List of milestones
            if len(timeline_data) < 2:
                findings.append("Timeline has fewer than 2 distinct milestones.")
                alerts.append(
                    AuditAlert(
                        severity=AlertSeverity.WARNING,
                        category="TIMELINE_SPARSE",
                        message="Timeline contains fewer than 2 milestone entries.",
                        field_name="timeline",
                        suggestion="Provide detailed chronological progression including symptom onset, admission, diagnosis, therapy, and follow-up."
                    )
                )
                is_valid = False
            else:
                findings.append(f"Structured timeline contains {len(timeline_data)} chronological milestone entries.")
                # Check for day numbers or dates
                prev_day = -999999
                for idx, entry in enumerate(timeline_data):
                    if isinstance(entry, dict):
                        day = entry.get("relative_day") if "relative_day" in entry else entry.get("day")
                        if day is not None:
                            try:
                                day_num = int(day)
                                if day_num < prev_day:
                                    is_valid = False
                                    alerts.append(
                                        AuditAlert(
                                            severity=AlertSeverity.CRITICAL,
                                            category="CHRONOLOGY_INVERSION",
                                            message=f"Timeline sequence inversion detected at step {idx + 1}: Day {day_num} precedes Day {prev_day}.",
                                            field_name="timeline",
                                            suggestion="Ensure all timeline milestones are ordered chronologically."
                                        )
                                    )
                                prev_day = day_num
                            except (ValueError, TypeError):
                                pass
        elif isinstance(timeline_data, str):
            if len(timeline_data.strip()) < 30:
                findings.append("Narrative timeline is too brief.")
                is_valid = False
            else:
                findings.append("Narrative timeline description present.")
        else:
            is_valid = False
            findings.append(f"Unsupported timeline type: {type(timeline_data).__name__}.")
            alerts.append(
                AuditAlert(
                    severity=AlertSeverity.WARNING,
                    category="TIMELINE_FORMAT",
                    message="Timeline must be a narrative string or a list of milestone objects.",
                    field_name="timeline",
                    suggestion="Provide a timeline narrative or ordered milestone list."
                )
            )

        return is_valid, findings, alerts


# ==============================================================================
# CORE VALIDATOR ENGINE
# ==============================================================================

class CARECaseReportValidator:
    """
    Primary validation engine for clinical case reports against the CARE 2013 Checklist.
    Supports structured JSON data, Python dictionaries, or plain text / markdown manuscripts.
    """

    def __init__(self, phi_strict: bool = True):
        self.phi_strict = phi_strict

    def validate(self, payload: Union[Dict[str, Any], str]) -> CAREValidationReport:
        """
        Validates a case report payload against the CARE 2013 guideline checklist.
        """
        if isinstance(payload, str):
            case_data = self._parse_text_manuscript(payload)
        elif isinstance(payload, dict):
            case_data = payload
        else:
            raise ValueError(f"Expected dict or str payload, got {type(payload).__name__}")

        raw_text_corpus = self._extract_all_text(case_data)
        alerts: List[AuditAlert] = []

        # 1. PHI / Privacy Audit
        phi_alerts = PHISecurityAuditor.audit_text(raw_text_corpus) if self.phi_strict else []
        alerts.extend(phi_alerts)
        phi_violations = [a.message for a in phi_alerts]

        # 2. Timeline Evaluation
        timeline_valid, timeline_findings, timeline_alerts = TimelineChronologyAuditor.evaluate_timeline(
            case_data.get("timeline")
        )
        alerts.extend(timeline_alerts)

        # 3. Item-by-item CARE checklist evaluations
        item_evaluations: List[ItemEvaluation] = []
        section_raw_scores: Dict[str, List[float]] = {}

        for spec in CARE_CHECKLIST_SPEC:
            item_eval = self._evaluate_item(spec, case_data, timeline_valid, timeline_findings)
            item_evaluations.append(item_eval)

            sec = spec["section"]
            if sec not in section_raw_scores:
                section_raw_scores[sec] = []
            section_raw_scores[sec].append(item_eval.score)

        # Calculate section scores and overall weighted compliance
        total_weight = sum(item.weight for item in item_evaluations)
        weighted_score_sum = sum(item.score * item.weight for item in item_evaluations)
        overall_compliance = (weighted_score_sum / total_weight) * 100.0 if total_weight > 0 else 0.0

        # Section percentage scores
        section_scores = {
            sec: (sum(scores) / len(scores)) * 100.0
            for sec, scores in section_raw_scores.items()
        }

        # Compliance Tier
        if overall_compliance >= 90.0:
            tier = ComplianceTier.FULLY_COMPLIANT
        elif overall_compliance >= 75.0:
            tier = ComplianceTier.SUBSTANTIALLY_COMPLIANT
        elif overall_compliance >= 50.0:
            tier = ComplianceTier.MODERATELY_COMPLIANT
        else:
            tier = ComplianceTier.NON_COMPLIANT

        # Metrics counts
        items_met = sum(1 for item in item_evaluations if item.status == ComplianceStatus.MET)
        items_partially = sum(1 for item in item_evaluations if item.status == ComplianceStatus.PARTIALLY_MET)
        items_unmet = sum(1 for item in item_evaluations if item.status == ComplianceStatus.UNMET)

        # Strengths & Deficiencies
        strengths = [item.title for item in item_evaluations if item.status == ComplianceStatus.MET]
        deficiencies = [
            f"Item {item.item_id} ({item.title}): {'; '.join(item.recommendations)}"
            for item in item_evaluations
            if item.status in (ComplianceStatus.UNMET, ComplianceStatus.PARTIALLY_MET) and item.recommendations
        ]

        actionable = [
            f"[{item.item_id}] {item.section} - {rec}"
            for item in item_evaluations
            for rec in item.recommendations
        ]

        manuscript_title = str(case_data.get("title") or "Untitled Case Report")

        return CAREValidationReport(
            manuscript_title=manuscript_title,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            overall_compliance_score=overall_compliance,
            compliance_tier=tier,
            items_total=len(item_evaluations),
            items_met=items_met,
            items_partially_met=items_partially,
            items_unmet=items_unmet,
            section_scores=section_scores,
            item_evaluations=item_evaluations,
            alerts=alerts,
            phi_violations=phi_violations,
            timeline_valid=timeline_valid,
            summary_strengths=strengths,
            summary_deficiencies=deficiencies,
            actionable_checklist=actionable,
        )

    def _evaluate_item(
        self,
        spec: Dict[str, Any],
        data: Dict[str, Any],
        timeline_valid: bool,
        timeline_findings: List[str]
    ) -> ItemEvaluation:
        item_id = spec["item_id"]
        sec = spec["section"]
        title = spec["title"]
        weight = spec["weight"]

        findings: List[str] = []
        recommendations: List[str] = []
        score = 0.0

        # ITEM 1: Title
        if item_id == "1":
            title_text = str(data.get("title") or "").strip()
            if not title_text:
                status = ComplianceStatus.UNMET
                findings.append("No title provided.")
                recommendations.append("Add a descriptive title incorporating the words 'Case Report' or 'Case Study'.")
            else:
                has_case_report = "case report" in title_text.lower()
                has_case_variant = any(w in title_text.lower() for w in ["case study", "case presentation"])
                has_substance = len(title_text.split()) >= 4
                if has_case_report and has_substance:
                    status = ComplianceStatus.MET
                    score = 1.0
                    findings.append(f"Title clearly states case report format: '{title_text}'")
                elif has_case_report:
                    status = ComplianceStatus.PARTIALLY_MET
                    score = 0.7
                    findings.append("Title identifies case report format but lacks specific disease/intervention details.")
                    recommendations.append("Specify the exact condition, presentation, or intervention in the title.")
                elif has_case_variant:
                    status = ComplianceStatus.PARTIALLY_MET
                    score = 0.5
                    findings.append("Title uses a case-study/case-presentation label rather than the CARE wording 'case report'.")
                    recommendations.append("Use the words 'case report' in the manuscript title.")
                else:
                    status = ComplianceStatus.PARTIALLY_MET
                    score = 0.4
                    findings.append(f"Title describes clinical topic but lacks the phrase 'Case Report' or 'Case Study'.")
                    recommendations.append("Explicitly include 'Case Report' or 'Case Study' in the manuscript title.")

        # ITEM 2: Keywords
        elif item_id == "2":
            keywords = data.get("keywords") or data.get("key_words") or []
            if isinstance(keywords, str):
                keywords = [k.strip() for k in keywords.split(",") if k.strip()]
            elif not isinstance(keywords, (list, tuple)):
                keywords = [str(keywords)] if keywords else []
            count = len(keywords)
            normalized_keywords = [str(k).strip().lower() for k in keywords]
            has_case_report_keyword = "case report" in normalized_keywords
            if 2 <= count <= 5 and has_case_report_keyword:
                status = ComplianceStatus.MET
                score = 1.0
                findings.append(f"Provided {count} keywords including 'case report': {', '.join(map(str, keywords))}.")
            elif 2 <= count <= 5:
                status = ComplianceStatus.PARTIALLY_MET
                score = 0.8
                findings.append(f"Provided {count} keywords but omitted the CARE-recommended keyword 'case report'.")
                recommendations.append("Include 'case report' among the 2 to 5 keywords.")
            elif count > 5:
                status = ComplianceStatus.PARTIALLY_MET
                score = 0.8
                findings.append(f"Provided {count} keywords (CARE recommends 2 to 5 keywords).")
                recommendations.append("Refine the list to 2 to 5 relevant keywords and include 'case report'.")
            elif count == 1:
                status = ComplianceStatus.PARTIALLY_MET
                score = 0.5
                findings.append("Only 1 keyword provided.")
                recommendations.append("Provide 2 to 5 relevant keywords, including 'case report'.")
            else:
                status = ComplianceStatus.UNMET
                findings.append("No keywords provided.")
                recommendations.append("Provide 2 to 5 key words identifying diagnoses or interventions, including 'case report'.")

        # ITEM 3a: Abstract - Introduction
        elif item_id == "3a":
            val = self._get_nested(data, ["abstract", "introduction"]) or self._get_nested(data, ["abstract", "background"])
            score, status, f, r = self._eval_text_presence(val, "Abstract introduction / case uniqueness", min_len=20)
            findings.extend(f)
            recommendations.extend(r)

        # ITEM 3b: Abstract - Main symptoms/findings
        elif item_id == "3b":
            val = self._get_nested(data, ["abstract", "symptoms"]) or self._get_nested(data, ["abstract", "clinical_findings"]) or self._get_nested(data, ["abstract", "presentation"])
            score, status, f, r = self._eval_text_presence(val, "Abstract clinical findings / presentation", min_len=20)
            findings.extend(f)
            recommendations.extend(r)

        # ITEM 3c: Abstract - Diagnoses, Interventions, Outcomes
        elif item_id == "3c":
            val = self._get_nested(data, ["abstract", "diagnoses_interventions_outcomes"]) or self._get_nested(data, ["abstract", "interventions"]) or self._get_nested(data, ["abstract", "treatment"])
            score, status, f, r = self._eval_text_presence(val, "Abstract diagnoses, interventions, and outcomes", min_len=25)
            findings.extend(f)
            recommendations.extend(r)

        # ITEM 3d: Abstract - Conclusion
        elif item_id == "3d":
            val = self._get_nested(data, ["abstract", "conclusion"]) or self._get_nested(data, ["abstract", "lessons"])
            score, status, f, r = self._eval_text_presence(val, "Abstract conclusion / take-away lesson", min_len=20)
            findings.extend(f)
            recommendations.extend(r)

        # ITEM 4: Introduction
        elif item_id == "4":
            intro = data.get("introduction") or data.get("background")
            score, status, f, r = self._eval_text_presence(intro, "Manuscript introduction and literature background", min_len=50)
            findings.extend(f)
            recommendations.extend(r)

        # ITEM 5a: Patient Demographics & De-identification
        elif item_id == "5a":
            patient_info = data.get("patient_information") or data.get("patient") or {}
            if isinstance(patient_info, dict):
                age = patient_info.get("age")
                sex = patient_info.get("sex") or patient_info.get("gender")
                ethnicity = patient_info.get("ethnicity") or patient_info.get("race")
                occupation = patient_info.get("occupation")
                has_core = age is not None and sex is not None
                if has_core:
                    status = ComplianceStatus.MET
                    score = 1.0
                    findings.append(f"Demographics documented: Age={age}, Sex={sex}" + (f", Ethnicity={ethnicity}" if ethnicity else ""))
                elif age is not None or sex is not None:
                    status = ComplianceStatus.PARTIALLY_MET
                    score = 0.6
                    findings.append("Partial demographic profile provided (missing age or biological sex).")
                    recommendations.append("Document both patient age and biological sex.")
                else:
                    status = ComplianceStatus.UNMET
                    findings.append("Demographic information missing.")
                    recommendations.append("Provide de-identified demographic details (age, sex, ethnicity, occupation if relevant).")
            elif isinstance(patient_info, str) and len(patient_info.strip()) > 15:
                status = ComplianceStatus.MET
                score = 0.9
                findings.append("Narrative patient demographic description provided.")
            else:
                status = ComplianceStatus.UNMET
                findings.append("Patient demographic information missing.")
                recommendations.append("Provide patient age, sex, and relevant background.")

        # ITEM 5b: Chief Complaint
        elif item_id == "5b":
            cc = self._get_nested(data, ["patient_information", "chief_complaint"]) or data.get("chief_complaint") or self._get_nested(data, ["patient", "chief_complaint"])
            score, status, f, r = self._eval_text_presence(cc, "Chief complaint / presenting symptoms", min_len=10)
            findings.extend(f)
            recommendations.extend(r)

        # ITEM 5c: Medical, Family, Psychosocial History
        elif item_id == "5c":
            hist = self._get_nested(data, ["patient_information", "history"]) or data.get("medical_history") or self._get_nested(data, ["patient_information", "medical_history"])
            score, status, f, r = self._eval_text_presence(hist, "Medical, family, and psychosocial history", min_len=20)
            findings.extend(f)
            recommendations.extend(r)

        # ITEM 5d: Relevant Past Interventions
        elif item_id == "5d":
            past_tx = self._get_nested(data, ["patient_information", "past_interventions"]) or data.get("past_interventions")
            score, status, f, r = self._eval_text_presence(past_tx, "Past interventions and their outcomes", min_len=10, optional=True)
            findings.extend(f)
            recommendations.extend(r)

        # ITEM 6: Clinical Findings (Physical Exam)
        elif item_id == "6":
            pe = data.get("clinical_findings") or data.get("physical_examination") or self._get_nested(data, ["clinical_findings", "physical_exam"])
            score, status, f, r = self._eval_text_presence(pe, "Physical examination and clinical findings", min_len=25)
            findings.extend(f)
            recommendations.extend(r)

        # ITEM 7: Timeline
        elif item_id == "7":
            if timeline_valid:
                status = ComplianceStatus.MET
                score = 1.0
                findings.extend(timeline_findings)
            else:
                tl = data.get("timeline")
                if tl:
                    status = ComplianceStatus.PARTIALLY_MET
                    score = 0.5
                    findings.extend(timeline_findings)
                    recommendations.append("Format timeline with ordered dates/relative days and corresponding milestones.")
                else:
                    status = ComplianceStatus.UNMET
                    findings.append("No timeline table or milestone chronology provided.")
                    recommendations.append("Include a chronological table or figure of patient trajectory (CARE item 7).")

        # ITEM 8a: Diagnostic Methods (Labs, Imaging)
        elif item_id == "8a":
            labs = data.get("diagnostic_assessment") or data.get("diagnostic_methods") or data.get("investigations")
            score, status, f, r = self._eval_text_presence(labs, "Diagnostic testing methods and laboratory/imaging results", min_len=25)
            findings.extend(f)
            recommendations.extend(r)

        # ITEM 8b: Diagnostic Challenges
        elif item_id == "8b":
            challenges = self._get_nested(data, ["diagnostic_assessment", "challenges"]) or data.get("diagnostic_challenges")
            score, status, f, r = self._eval_text_presence(challenges, "Diagnostic challenges and diagnostic delays", min_len=15, optional=True)
            findings.extend(f)
            recommendations.extend(r)

        # ITEM 8c: Diagnostic Reasoning / Differential
        elif item_id == "8c":
            diff = self._get_nested(data, ["diagnostic_assessment", "differential_diagnosis"]) or data.get("differential_diagnosis") or self._get_nested(data, ["diagnostic_assessment", "reasoning"])
            score, status, f, r = self._eval_text_presence(diff, "Diagnostic reasoning and differential diagnosis", min_len=20)
            findings.extend(f)
            recommendations.extend(r)

        # ITEM 8d: Prognostic Characteristics / Staging
        elif item_id == "8d":
            prog = self._get_nested(data, ["diagnostic_assessment", "prognosis"]) or data.get("prognosis") or data.get("staging")
            score, status, f, r = self._eval_text_presence(prog, "Prognostic characteristics and staging", min_len=10, optional=True)
            findings.extend(f)
            recommendations.extend(r)

        # ITEM 9a: Therapeutic Intervention Types
        elif item_id == "9a":
            tx = data.get("therapeutic_intervention") or data.get("treatment") or data.get("interventions")
            score, status, f, r = self._eval_text_presence(tx, "Types of therapeutic intervention", min_len=20)
            findings.extend(f)
            recommendations.extend(r)

        # ITEM 9b: Intervention Administration (Dosage, Route, Duration)
        elif item_id == "9b":
            admin = self._get_nested(data, ["therapeutic_intervention", "administration"]) or self._get_nested(data, ["treatment", "dosage"]) or data.get("intervention_dosage")
            score, status, f, r = self._eval_text_presence(admin, "Intervention dosage, route, frequency, and duration", min_len=15)
            findings.extend(f)
            recommendations.extend(r)

        # ITEM 9c: Changes in Intervention with Rationale
        elif item_id == "9c":
            changes = self._get_nested(data, ["therapeutic_intervention", "changes"]) or data.get("treatment_changes")
            score, status, f, r = self._eval_text_presence(changes, "Therapeutic changes and rationale", min_len=10, optional=True)
            findings.extend(f)
            recommendations.extend(r)

        # ITEM 10a: Clinician and Patient-Assessed Outcomes
        elif item_id == "10a":
            outcomes = data.get("outcomes") or data.get("follow_up_and_outcomes") or self._get_nested(data, ["follow_up", "outcomes"])
            score, status, f, r = self._eval_text_presence(outcomes, "Clinician and patient-assessed clinical outcomes", min_len=20)
            findings.extend(f)
            recommendations.extend(r)

        # ITEM 10b: Follow-up Diagnostic Tests
        elif item_id == "10b":
            fu_tests = self._get_nested(data, ["follow_up_and_outcomes", "follow_up_tests"]) or self._get_nested(data, ["follow_up", "testing"]) or data.get("follow_up_tests")
            score, status, f, r = self._eval_text_presence(fu_tests, "Follow-up diagnostic testing results", min_len=15, optional=True)
            findings.extend(f)
            recommendations.extend(r)

        # ITEM 10c: Intervention Adherence and Tolerability
        elif item_id == "10c":
            adh = self._get_nested(data, ["follow_up_and_outcomes", "adherence"]) or self._get_nested(data, ["treatment", "adherence"]) or data.get("adherence")
            score, status, f, r = self._eval_text_presence(adh, "Intervention adherence and patient tolerability assessment", min_len=10)
            findings.extend(f)
            recommendations.extend(r)

        # ITEM 10d: Adverse and Unanticipated Events
        elif item_id == "10d":
            adv = self._get_nested(data, ["follow_up_and_outcomes", "adverse_events"]) or data.get("adverse_events")
            score, status, f, r = self._eval_text_presence(adv, "Adverse and unanticipated events (or explicit note of none)", min_len=10)
            findings.extend(f)
            recommendations.extend(r)

        # ITEM 11a: Discussion - Strengths and Limitations
        elif item_id == "11a":
            sl = self._get_nested(data, ["discussion", "strengths_and_limitations"]) or self._get_nested(data, ["discussion", "limitations"]) or data.get("limitations")
            score, status, f, r = self._eval_text_presence(sl, "Discussion of case management strengths and limitations", min_len=25)
            findings.extend(f)
            recommendations.extend(r)

        # ITEM 11b: Discussion - Literature Context
        elif item_id == "11b":
            lit = self._get_nested(data, ["discussion", "literature_review"]) or data.get("discussion")
            score, status, f, r = self._eval_text_presence(lit, "Discussion of relevant medical literature", min_len=40)
            findings.extend(f)
            recommendations.extend(r)

        # ITEM 11c: Discussion - Scientific Rationale
        elif item_id == "11c":
            rat = self._get_nested(data, ["discussion", "scientific_rationale"]) or self._get_nested(data, ["discussion", "rationale"])
            score, status, f, r = self._eval_text_presence(rat, "Scientific rationale and mechanism for conclusions", min_len=25)
            findings.extend(f)
            recommendations.extend(r)

        # ITEM 11d: Discussion - Take-away Lessons
        elif item_id == "11d":
            lessons = self._get_nested(data, ["discussion", "take_away_lessons"]) or self._get_nested(data, ["discussion", "conclusion"]) or data.get("learning_points")
            score, status, f, r = self._eval_text_presence(lessons, "Primary takeaway lessons for clinical practice", min_len=20)
            findings.extend(f)
            recommendations.extend(r)

        # ITEM 12: Patient Perspective
        elif item_id == "12":
            persp = data.get("patient_perspective") or self._get_nested(data, ["patient_information", "perspective"])
            score, status, f, r = self._eval_text_presence(persp, "Patient perspective, reflections, or narrative", min_len=15, optional=True)
            findings.extend(f)
            recommendations.extend(r)

        # ITEM 13: Informed Consent
        elif item_id == "13":
            consent = data.get("informed_consent") or data.get("ethics_statement") or self._get_nested(data, ["declarations", "consent"])
            score, status, f, r = self._eval_text_presence(consent, "Informed consent or institutional ethics statement", min_len=15)
            findings.extend(f)
            recommendations.extend(r)

        else:
            status = ComplianceStatus.NOT_APPLICABLE
            score = 1.0

        return ItemEvaluation(
            item_id=item_id,
            section=sec,
            title=title,
            status=status,
            score=score,
            weight=weight,
            findings=findings,
            recommendations=recommendations,
        )

    # --------------------------------------------------------------------------
    # Helper validation routines
    # --------------------------------------------------------------------------

    @staticmethod
    def _get_nested(d: Any, keys: List[str]) -> Optional[Any]:
        curr = d
        for k in keys:
            if isinstance(curr, dict) and k in curr:
                curr = curr[k]
            else:
                return None
        return curr

    @staticmethod
    def _eval_text_presence(
        val: Any,
        label: str,
        min_len: int = 20,
        optional: bool = False
    ) -> Tuple[float, ComplianceStatus, List[str], List[str]]:
        findings = []
        recommendations = []

        if val is None:
            if optional:
                return 0.5, ComplianceStatus.PARTIALLY_MET, [f"{label} not specified (optional or case-dependent)."], [f"Consider adding {label.lower()} if applicable."]
            return 0.0, ComplianceStatus.UNMET, [f"{label} is missing."], [f"Document {label.lower()} to satisfy CARE requirements."]

        text = ""
        if isinstance(val, str):
            text = val.strip()
        elif isinstance(val, (list, dict)):
            text = json.dumps(val)

        length = len(text)
        if length >= min_len:
            findings.append(f"{label} is adequately documented ({length} chars).")
            return 1.0, ComplianceStatus.MET, findings, recommendations
        elif length > 0:
            findings.append(f"{label} is briefly mentioned ({length} chars, expected >= {min_len}).")
            recommendations.append(f"Expand on {label.lower()} with additional clinical specifics.")
            return 0.5, ComplianceStatus.PARTIALLY_MET, findings, recommendations
        else:
            if optional:
                return 0.5, ComplianceStatus.PARTIALLY_MET, [f"{label} is empty."], [f"Consider adding {label.lower()} if applicable."]
            return 0.0, ComplianceStatus.UNMET, [f"{label} is empty."], [f"Provide substantive details for {label.lower()}."]

    def _extract_all_text(self, obj: Any) -> str:
        if isinstance(obj, str):
            return obj
        elif isinstance(obj, dict):
            return " ".join(self._extract_all_text(v) for v in obj.values())
        elif isinstance(obj, list):
            return " ".join(self._extract_all_text(i) for i in obj)
        return str(obj)

    def _parse_text_manuscript(self, raw_text: str) -> Dict[str, Any]:
        """Heuristically parses raw text or markdown manuscript into CARE sections."""
        lines = raw_text.splitlines()
        parsed: Dict[str, Any] = {
            "title": "",
            "keywords": [],
            "abstract": {},
            "introduction": "",
            "patient_information": {},
            "clinical_findings": "",
            "timeline": [],
            "diagnostic_assessment": {},
            "therapeutic_intervention": {},
            "follow_up_and_outcomes": {},
            "discussion": {},
            "patient_perspective": "",
            "informed_consent": "",
        }

        current_section: Optional[str] = None
        current_buffer: List[str] = []

        for line in lines:
            stripped = line.strip()
            lower_clean = re.sub(r"^#+\s*", "", stripped).lower().rstrip(":")

            header_map = {
                "abstract": "abstract",
                "introduction": "introduction",
                "background": "introduction",
                "case presentation": "patient_information",
                "patient information": "patient_information",
                "clinical findings": "clinical_findings",
                "physical examination": "clinical_findings",
                "timeline": "timeline",
                "diagnostic assessment": "diagnostic_assessment",
                "investigations": "diagnostic_assessment",
                "treatment": "therapeutic_intervention",
                "therapeutic intervention": "therapeutic_intervention",
                "follow-up and outcomes": "follow_up_and_outcomes",
                "outcomes": "follow_up_and_outcomes",
                "discussion": "discussion",
                "patient perspective": "patient_perspective",
                "informed consent": "informed_consent",
                "conclusion": "discussion",
            }

            matched_sec = None
            for key, target in header_map.items():
                if lower_clean == key or lower_clean.startswith(key):
                    matched_sec = target
                    break

            if matched_sec:
                if current_section and current_buffer:
                    self._assign_buffer(parsed, current_section, "\n".join(current_buffer).strip())
                    current_buffer = []
                current_section = matched_sec
            else:
                if stripped.lower().startswith("keywords:") or stripped.lower().startswith("key words:"):
                    kw_part = stripped.split(":", 1)[1]
                    parsed["keywords"] = [k.strip() for k in kw_part.split(",") if k.strip()]
                elif not current_section and stripped and not parsed["title"]:
                    if stripped.startswith("# "):
                        parsed["title"] = stripped[2:].strip()
                    elif "case report" in stripped.lower() or "patient" in stripped.lower():
                        parsed["title"] = stripped
                else:
                    current_buffer.append(line)

        if current_section and current_buffer:
            self._assign_buffer(parsed, current_section, "\n".join(current_buffer).strip())

        return parsed

    @staticmethod
    def _matching_sentences(text: str, patterns: List[str]) -> str:
        """Return only sentences that contain at least one requested cue."""
        sentences = [
            part.strip()
            for part in re.split(r"(?<=[.!?;])\s+|\n+", text)
            if part.strip()
        ]
        matched = [
            sentence
            for sentence in sentences
            if any(re.search(pattern, sentence, re.IGNORECASE) for pattern in patterns)
        ]
        return " ".join(matched)

    @staticmethod
    def _merge_section_value(container: Dict[str, Any], key: str, value: str) -> None:
        """Append non-empty parsed text without discarding an earlier section."""
        value = value.strip()
        if not value:
            return
        existing = str(container.get(key) or "").strip()
        container[key] = f"{existing} {value}".strip() if existing else value

    def _assign_buffer(self, target_dict: Dict[str, Any], section: str, text: str) -> None:
        if section == "abstract":
            abstract = target_dict.get("abstract")
            if not isinstance(abstract, dict):
                abstract = {}
                target_dict["abstract"] = abstract

            cues = {
                "introduction": [r"\b(unique|rare|unusual|novel|literature|previously|first)\b"],
                "symptoms": [r"\b(presented|presentation|symptom|complaint|finding|examination)\b"],
                "diagnoses_interventions_outcomes": [r"\b(diagnos|treat|therap|intervention|outcome|recover|improv|resolv)\w*\b"],
                "conclusion": [r"\b(conclusion|lesson|highlight|suggest|demonstrat|importance|important|should|recommend)\w*\b"],
            }
            for key, patterns in cues.items():
                self._merge_section_value(abstract, key, self._matching_sentences(text, patterns))

        elif section == "patient_information":
            age_match = re.search(
                r"\b(?:(\d{1,3})\s*[-–— ]?years?[-–— ]?old|aged\s+(\d{1,3}))\b",
                text,
                re.IGNORECASE,
            )
            age = None
            if age_match:
                candidate = int(age_match.group(1) or age_match.group(2))
                if 0 <= candidate <= 125:
                    age = candidate

            sex = None
            if re.search(r"\b(female|woman|girl)\b", text, re.IGNORECASE):
                sex = "Female"
            elif re.search(r"\b(male|man|boy)\b", text, re.IGNORECASE):
                sex = "Male"

            patient = target_dict.get("patient_information")
            if not isinstance(patient, dict):
                patient = {}
                target_dict["patient_information"] = patient
            if age is not None:
                patient["age"] = age
            if sex is not None:
                patient["sex"] = sex

            chief = self._matching_sentences(
                text,
                [r"\b(presented|presentation|complaint|symptom|concern|pain|fever|seizure)\w*\b"],
            )
            history = self._matching_sentences(
                text,
                [r"\b(history|past|previous|prior|family|social|psychosocial|comorbid)\w*\b"],
            )
            self._merge_section_value(patient, "chief_complaint", chief)
            self._merge_section_value(patient, "history", history)

        elif section == "diagnostic_assessment":
            diagnostic = target_dict.get("diagnostic_assessment")
            if not isinstance(diagnostic, dict):
                diagnostic = {}
                target_dict["diagnostic_assessment"] = diagnostic
            self._merge_section_value(diagnostic, "diagnostic_methods", text)
            self._merge_section_value(
                diagnostic,
                "differential_diagnosis",
                self._matching_sentences(
                    text,
                    [r"\b(differential|considered|excluded|rule[sd]? out|alternative diagnos)\w*\b"],
                ),
            )
            self._merge_section_value(
                diagnostic,
                "challenges",
                self._matching_sentences(
                    text,
                    [r"\b(challenge|delay|uncertain|difficult|atypical)\w*\b"],
                ),
            )

        elif section == "therapeutic_intervention":
            intervention = target_dict.get("therapeutic_intervention")
            if not isinstance(intervention, dict):
                intervention = {}
                target_dict["therapeutic_intervention"] = intervention
            self._merge_section_value(intervention, "treatment", text)
            self._merge_section_value(
                intervention,
                "administration",
                self._matching_sentences(
                    text,
                    [
                        r"\b\d+(?:\.\d+)?\s*(?:mg|g|mcg|µg|ml|units?|mg/kg|g/kg)\b",
                        r"\b(daily|weekly|twice|intravenous|intravenously|oral|orally|route|duration)\b",
                    ],
                ),
            )
            self._merge_section_value(
                intervention,
                "changes",
                self._matching_sentences(
                    text,
                    [r"\b(changed|switched|escalat|de-escalat|discontinued|stopped|because|due to)\w*\b"],
                ),
            )

        elif section == "follow_up_and_outcomes":
            follow_up = target_dict.get("follow_up_and_outcomes")
            if not isinstance(follow_up, dict):
                follow_up = {}
                target_dict["follow_up_and_outcomes"] = follow_up
            self._merge_section_value(follow_up, "outcomes", text)
            self._merge_section_value(
                follow_up,
                "adherence",
                self._matching_sentences(
                    text,
                    [r"\b(adher|compliance|missed|completed|tolerat)\w*\b"],
                ),
            )
            self._merge_section_value(
                follow_up,
                "adverse_events",
                self._matching_sentences(
                    text,
                    [r"\b(adverse|complication|side effect|reaction|unanticipated)\w*\b"],
                ),
            )

        elif section == "discussion":
            discussion = target_dict.get("discussion")
            if not isinstance(discussion, dict):
                discussion = {}
                target_dict["discussion"] = discussion
            self._merge_section_value(
                discussion,
                "literature_review",
                self._matching_sentences(
                    text,
                    [r"\b(literature|study|studies|reported|previous|evidence|reference|et al)\b"],
                ),
            )
            self._merge_section_value(
                discussion,
                "strengths_and_limitations",
                self._matching_sentences(text, [r"\b(strength|limitation)\w*\b"]),
            )
            self._merge_section_value(
                discussion,
                "scientific_rationale",
                self._matching_sentences(
                    text,
                    [r"\b(mechanism|rationale|because|pathophysi|mediated|supports)\w*\b"],
                ),
            )
            self._merge_section_value(
                discussion,
                "take_away_lessons",
                self._matching_sentences(
                    text,
                    [r"\b(lesson|take-away|takeaway|conclusion|should|recommend|highlight|importance|important|warrant)\w*\b"],
                ),
            )

        elif section == "timeline":
            target_dict["timeline"] = text
        else:
            target_dict[section] = text


# ==============================================================================
# REPORT FORMATTERS
# ==============================================================================

def format_markdown_report(report: CAREValidationReport) -> str:
    """Formats validation results as a clean GitHub Flavored Markdown document."""
    lines = [
        f"# CARE Case Report Validation Audit",
        f"**Manuscript Title:** {report.manuscript_title}",
        f"**Audit Timestamp:** `{report.timestamp}`",
        f"**Heuristic Checklist Coverage:** **{report.overall_compliance_score:.1f}%** ({report.compliance_tier.value})",
        "",
        "## Summary Metrics",
        f"- **Total Checklist Items:** {report.items_total}",
        f"- **Items Fully Met:** {report.items_met} :white_check_mark:",
        f"- **Items Partially Met:** {report.items_partially_met} :warning:",
        f"- **Items Unmet:** {report.items_unmet} :x:",
        f"- **Timeline Valid:** {'Yes :white_check_mark:' if report.timeline_valid else 'Deficient :warning:'}",
        "",
        "## Section Scores",
        "| Section | Coverage (%) |",
        "| :--- | :--- |",
    ]
    for sec, score in report.section_scores.items():
        lines.append(f"| {sec} | {score:.1f}% |")

    if report.phi_violations:
        lines.extend([
            "",
            "## :rotating_light: Critical PHI / Privacy Alerts",
        ])
        for v in report.phi_violations:
            lines.append(f"- :no_entry_sign: {v}")

    lines.extend([
        "",
        "## CARE 2013 Item-by-Item Checklist Breakdown",
        "| Item | Section | Status | Score | Findings & Recommendations |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ])
    for item in report.item_evaluations:
        status_icon = "MET :white_check_mark:" if item.status == ComplianceStatus.MET else ("PARTIAL :warning:" if item.status == ComplianceStatus.PARTIALLY_MET else "UNMET :x:")
        notes = " ".join(item.findings)
        if item.recommendations:
            notes += " **Rec:** " + " ".join(item.recommendations)
        notes = notes.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {item.item_id} | {item.section} | {status_icon} | {item.score * 100:.0f}% | {notes} |")

    if report.actionable_checklist:
        lines.extend([
            "",
            "## Author Action Items",
        ])
        for idx, act in enumerate(report.actionable_checklist, 1):
            lines.append(f"{idx}. {act}")

    return "\n".join(lines)
