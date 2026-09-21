#!/usr/bin/env python3
"""
CARE Case Report Validator - Command Line Interface
===================================================
Command-line tools for rule-based review of case report drafts against the CARE 2013 checklist.

Usage:
    python cli.py validate --file case_report.json
    python cli.py validate --file manuscript.md --format markdown
    python cli.py interactive
    python cli.py benchmark
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

from care_validator import (
    CARECaseReportValidator,
    CAREValidationReport,
    ComplianceStatus,
    ComplianceTier,
    format_markdown_report,
)


def get_sample_compliant_report() -> Dict[str, Any]:
    """Returns a fully compliant reference CARE case report."""
    return {
        "title": "Atypical Presentation of Anti-NMDAR Encephalitis in an Adolescent: A Case Report",
        "keywords": ["Anti-NMDAR encephalitis", "Autoimmune encephalitis", "Psychosis", "Immunotherapy", "Case report"],
        "abstract": {
            "introduction": "Anti-N-methyl-D-aspartate receptor (NMDAR) encephalitis is a rare severe autoimmune disorder with prominent psychiatric presentation.",
            "symptoms": "A 16-year-old female presented with acute behavioral disturbance, visual hallucinations, catatonia, and autonomic instability.",
            "diagnoses_interventions_outcomes": "CSF positive for GluN1-specific IgG antibodies. Treated with IV methylprednisolone, IVIG, and rituximab with full cognitive recovery at 6 months.",
            "conclusion": "Early suspicion and prompt multi-tiered immunotherapy are critical for favorable outcomes in pediatric autoimmune encephalitis.",
        },
        "introduction": "Anti-NMDAR encephalitis, first described in 2007 by Dalmau et al., represents a critical differential diagnosis in acute psychiatric presentations among youth. Prompt diagnosis reduces neurological morbidity.",
        "patient_information": {
            "age": 16,
            "sex": "Female",
            "ethnicity": "Hispanic",
            "occupation": "High school student",
            "chief_complaint": "Acute onset auditory hallucinations, extreme agitation, and memory deficits lasting 5 days.",
            "history": "No prior psychiatric history, no illicit substance use, non-contributory family medical history.",
            "past_interventions": "Initially prescribed olanzapine 5 mg daily by emergency psychiatric services with no symptom resolution.",
        },
        "clinical_findings": "Temperature 38.6 C, HR 122 bpm, BP 142/90 mmHg. Patient was disoriented, catatonic, exhibiting facial dyskinesias and choreoathetoid arm movements. Cranial nerves intact.",
        "timeline": [
            {"relative_day": 1, "time_point": "Day 1", "event": "Acute psychiatric onset with insomnia and paranoia."},
            {"relative_day": 5, "time_point": "Day 5", "event": "Hospital admission with catatonia and hyperthermia."},
            {"relative_day": 7, "time_point": "Day 7", "event": "Lumbar puncture performed; CSF anti-NMDAR antibodies detected."},
            {"relative_day": 8, "time_point": "Day 8", "event": "Initiated pulse IV methylprednisolone 1g daily and IVIG 2g/kg over 5 days."},
            {"relative_day": 15, "time_point": "Day 15", "event": "Second-line therapy with rituximab 375 mg/m2 weekly x 4 doses."},
            {"relative_day": 30, "time_point": "Day 30", "event": "Significant neurological improvement and discharge to rehabilitation."},
            {"relative_day": 180, "time_point": "Day 180 (Month 6)", "event": "Complete cognitive recovery with return to academic baseline."},
        ],
        "diagnostic_assessment": {
            "diagnostic_methods": "Brain MRI showed subtle bilateral hippocampal FLAIR hyperintensity. EEG showed diffuse slowing with extreme delta brush pattern. CSF testing confirmed high-titer IgG against NR1 subunit of NMDAR.",
            "challenges": "Initial presentation closely mimicked primary acute psychosis, causing a 4-day delay before neurology consultation.",
            "differential_diagnosis": "Primary psychiatric psychosis, viral encephalitis (HSV/VZV), toxic ingestion, lupus cerebritis.",
            "prognosis": "Modified Rankin Scale (mRS) score 5 at nadir; anticipated favorable recovery given early immunotherapy.",
        },
        "therapeutic_intervention": {
            "treatment": "High-dose IV methylprednisolone, intravenous immunoglobulin (IVIG), and rituximab monoclonal antibody.",
            "administration": "Methylprednisolone 1g IV daily for 5 days; IVIG 0.4 g/kg/day for 5 days; Rituximab 375 mg/m2 IV weekly for 4 weeks.",
            "changes": "Escalated to rituximab on Day 15 due to persistent dyskinesias and autonomic instability despite first-line agents.",
        },
        "follow_up_and_outcomes": {
            "outcomes": "At 6-month follow-up, patient achieved complete symptom resolution (mRS score 0) with normal MoCA cognitive screening (30/30).",
            "follow_up_tests": "Follow-up brain MRI at 3 months demonstrated complete resolution of FLAIR hyperintensities. Repeat CSF at 6 months showed negative antibody titers.",
            "adherence": "Patient completed all 4 scheduled rituximab infusions without missed doses.",
            "adverse_events": "No infusion-related adverse reactions or infectious complications observed.",
        },
        "discussion": {
            "strengths_and_limitations": "Strengths: Rapid antibody identification and prompt escalation to second-line rituximab. Limitation: Initial delay in LP due to psychiatric containment.",
            "literature_review": "Our findings align with international consensus guidelines (Titulaer et al., Lancet Neurol 2013) highlighting the efficacy of early B-cell depletion.",
            "scientific_rationale": "Autoantibody-mediated internalization of NMDAR clusters disrupts synaptic plasticity, which is reversible upon antibody clearance.",
            "take_away_lessons": "New-onset psychiatric symptoms accompanied by autonomic instability or dyskinesias in adolescents warrant urgent CSF autoantibody screening.",
        },
        "patient_perspective": "The patient and her parents reflected: 'We felt helpless when the psychiatric medications failed, but seeing her regain full personality and return to school within six months felt like a miracle.'",
        "informed_consent": "Written informed consent for publication of this clinical case and accompanying radiological images was obtained from the patient's legal guardian. Ethics committee approval was granted by the Institutional Review Board (IRB-2024-PED-041).",
    }


def run_validate(args: argparse.Namespace) -> int:
    validator = CARECaseReportValidator()

    if not os.path.exists(args.file):
        print(f"Error: File not found '{args.file}'", file=sys.stderr)
        return 1

    with open(args.file, "r", encoding="utf-8") as f:
        content = f.read()

    # Try JSON parse first, else treat as raw text/markdown
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        data = content

    report = validator.validate(data)

    if args.json or args.format == "json":
        out_json = json.dumps(report.to_dict(), indent=2)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as out_f:
                out_f.write(out_json)
            print(f"Validation report saved to {args.output}")
        else:
            print(out_json)
        return 0

    if args.format == "markdown":
        md_text = format_markdown_report(report)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as out_f:
                out_f.write(md_text)
            print(f"Markdown report saved to {args.output}")
        else:
            print(md_text)
        return 0

    # Formatted summary display
    print("=" * 70)
    print(f"  CARE 2013 CLINICAL CASE REPORT VALIDATION AUDIT")
    print("=" * 70)
    print(f"Manuscript: {report.manuscript_title}")
    print(f"Heuristic Checklist Coverage: {report.overall_compliance_score:.1f}% [{report.compliance_tier.value}]")
    print(f"Items Met: {report.items_met}/{report.items_total} | Partially Met: {report.items_partially_met} | Unmet: {report.items_unmet}")
    print(f"Timeline Valid: {'YES' if report.timeline_valid else 'NO / DEFICIENT'}")
    print("-" * 70)
    print("SECTION COVERAGE BREAKDOWN:")
    for sec, score in report.section_scores.items():
        bar = "#" * int(score / 5) + "." * (20 - int(score / 5))
        print(f"  {sec:<25} [{bar}] {score:>5.1f}%")

    if report.phi_violations:
        print("\n" + "!" * 70)
        print("  CRITICAL HIPAA / PHI WARNINGS:")
        for v in report.phi_violations:
            print(f"  - {v}")
        print("!" * 70)

    if report.actionable_checklist:
        print("-" * 70)
        print("RECOMMENDED REVISIONS:")
        for idx, act in enumerate(report.actionable_checklist[:10], 1):
            print(f"  {idx}. {act}")
        if len(report.actionable_checklist) > 10:
            print(f"  ... and {len(report.actionable_checklist) - 10} more items.")
    print("=" * 70)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as out_f:
            json.dump(report.to_dict(), out_f, indent=2)
        print(f"Full report exported to {args.output}")

    return 0


def run_benchmark(args: argparse.Namespace) -> int:
    validator = CARECaseReportValidator()
    print("Running CARE Guideline Benchmark Suite...")

    # Benchmark 1: Fully compliant gold-standard report
    sample_full = get_sample_compliant_report()
    rep_full = validator.validate(sample_full)
    print(f"\n[Benchmark 1] Gold-Standard Report: {rep_full.overall_compliance_score:.1f}% ({rep_full.compliance_tier.value})")
    assert rep_full.overall_compliance_score >= 90.0, "Gold-standard report should be >= 90%"
    assert rep_full.items_unmet == 0, "Gold-standard should have 0 unmet items"

    # Benchmark 2: Deficient report (missing consent, timeline, discussion)
    sample_deficient = {
        "title": "A Patient with Headache",
        "keywords": ["headache"],
        "abstract": "Patient had a headache and got better.",
        "patient_information": {"age": 50},
    }
    rep_def = validator.validate(sample_deficient)
    print(f"[Benchmark 2] Deficient Manuscript: {rep_def.overall_compliance_score:.1f}% ({rep_def.compliance_tier.value})")
    assert rep_def.overall_compliance_score < 50.0, "Deficient manuscript should score < 50%"

    # Benchmark 3: PHI Violation Detection
    sample_phi = get_sample_compliant_report()
    sample_phi["patient_information"]["history"] += " Patient SSN is 123-45-6789, MRN: 98765432."
    rep_phi = validator.validate(sample_phi)
    print(f"[Benchmark 3] PHI Injection Test: Detected {len(rep_phi.phi_violations)} PHI violation(s)")
    assert len(rep_phi.phi_violations) >= 2, "Should detect SSN and MRN"

    print("\nAll benchmark assertions PASSED successfully!\n")
    return 0


def run_interactive(args: argparse.Namespace) -> int:
    print("=" * 70)
    print("  CARE 2013 CASE REPORT CHECKLIST REVIEW")
    print("=" * 70)
    print("Enter details for each section (press Enter to skip if not applicable):\n")

    title = input("1. Manuscript Title: ").strip() or "Untitled Case Report"
    kw_str = input("2. Keywords (comma-separated): ").strip()
    keywords = [k.strip() for k in kw_str.split(",") if k.strip()] if kw_str else []

    print("\n-- Abstract --")
    abs_intro = input("   Abstract Introduction / Background: ").strip()
    abs_sym = input("   Abstract Symptoms / Clinical Findings: ").strip()
    abs_tx = input("   Abstract Diagnoses, Interventions, Outcomes: ").strip()
    abs_conc = input("   Abstract Conclusion: ").strip()

    intro = input("\n3. Introduction / Background: ").strip()

    print("\n-- Patient Information --")
    age_str = input("   Patient Age: ").strip()
    age = int(age_str) if age_str.isdigit() else None
    sex = input("   Patient Biological Sex (Male/Female/Other): ").strip() or None
    cc = input("   Chief Complaint: ").strip()
    history = input("   Medical/Family/Psychosocial History: ").strip()

    pe = input("\n4. Physical Examination / Clinical Findings: ").strip()

    print("\n-- Timeline --")
    timeline_str = input("   Timeline milestones (format: 'Day 1: Onset; Day 5: Admission' or text): ").strip()
    timeline = []
    if ";" in timeline_str:
        for idx, part in enumerate(timeline_str.split(";")):
            part = part.strip()
            if part:
                timeline.append({"relative_day": idx + 1, "time_point": f"Step {idx + 1}", "event": part})
    elif timeline_str:
        timeline = timeline_str

    print("\n-- Diagnostic Assessment --")
    diag_methods = input("   Diagnostic Methods (Labs, Imaging): ").strip()
    diff_diag = input("   Differential Diagnoses / Diagnostic Reasoning: ").strip()

    print("\n-- Therapeutic Intervention --")
    tx_desc = input("   Therapeutic Interventions (Drugs, Surgery, Dosages): ").strip()

    print("\n-- Follow-up & Outcomes --")
    outcomes = input("   Outcomes and Follow-up Findings: ").strip()
    adverse = input("   Adverse Events (or 'None'): ").strip()

    print("\n-- Discussion & Consent --")
    discussion = input("   Discussion & Learning Points: ").strip()
    consent = input("   Informed Consent Statement: ").strip()

    payload = {
        "title": title,
        "keywords": keywords,
        "abstract": {
            "introduction": abs_intro,
            "symptoms": abs_sym,
            "diagnoses_interventions_outcomes": abs_tx,
            "conclusion": abs_conc,
        },
        "introduction": intro,
        "patient_information": {
            "age": age,
            "sex": sex,
            "chief_complaint": cc,
            "history": history,
        },
        "clinical_findings": pe,
        "timeline": timeline,
        "diagnostic_assessment": {
            "diagnostic_methods": diag_methods,
            "differential_diagnosis": diff_diag,
        },
        "therapeutic_intervention": {
            "treatment": tx_desc,
            "administration": tx_desc,
        },
        "follow_up_and_outcomes": {
            "outcomes": outcomes,
            "adverse_events": adverse,
        },
        "discussion": {
            "literature_review": discussion,
            "take_away_lessons": discussion,
        },
        "informed_consent": consent,
    }

    validator = CARECaseReportValidator()
    report = validator.validate(payload)

    print("\n" + "=" * 70)
    print("  AUDIT RESULT")
    print("=" * 70)
    print(f"Heuristic Checklist Coverage: {report.overall_compliance_score:.1f}% [{report.compliance_tier.value}]")
    print(f"Items Met: {report.items_met}/{report.items_total} | Partially Met: {report.items_partially_met} | Unmet: {report.items_unmet}")
    print("\nSection Scores:")
    for sec, score in report.section_scores.items():
        print(f"  {sec:<25}: {score:.1f}%")

    if report.actionable_checklist:
        print("\nActionable Recommendations:")
        for idx, item in enumerate(report.actionable_checklist, 1):
            print(f"  {idx}. {item}")
    print("=" * 70)

    save_path = input("\nSave validation report to JSON file? (enter path or press Enter to skip): ").strip()
    if save_path:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2)
        print(f"Report saved to {save_path}")

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Review case-report drafts against CARE 2013 checklist criteria using deterministic heuristics."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # validate command
    val_p = subparsers.add_parser("validate", help="Validate a case report JSON or Markdown file")
    val_p.add_argument("--file", "-f", required=True, help="Path to input JSON, Markdown, or text file")
    val_p.add_argument("--format", choices=["summary", "markdown", "json"], default="summary", help="Output format")
    val_p.add_argument("--output", "-o", help="Output file path")
    val_p.add_argument("--json", action="store_true", help="Output pure JSON")

    # benchmark command
    subparsers.add_parser("benchmark", help="Run validation benchmarks")

    # interactive command
    subparsers.add_parser("interactive", help="Interactive section-by-section review")

    # sample command
    sample_p = subparsers.add_parser("sample", help="Write the bundled structured sample report to JSON")
    sample_p.add_argument("-o", "--output", default="sample_care_report.json", help="Output JSON path")

    # batch command
    batch_p = subparsers.add_parser("batch", help="Batch process case report records from CSV")
    batch_p.add_argument("-i", "--input", required=True, help="Path to input CSV")
    batch_p.add_argument("-o", "--output", default="care_audit_results.csv", help="Path to output CSV")

    args = parser.parse_args(argv)

    if args.command == "validate":
        return run_validate(args)
    elif args.command == "benchmark":
        return run_benchmark(args)
    elif args.command == "interactive":
        return run_interactive(args)
    elif args.command == "batch":
        return run_batch(args)
    elif args.command == "sample":
        sample = get_sample_compliant_report()
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(sample, f, indent=2)
        print(f"Sample compliant CARE report written to {args.output}")
        return 0
    else:
        # Default to interactive or help
        if len(sys.argv) == 1:
            parser.print_help()
            return 0
        parser.print_help()
        return 1


def run_batch(args: argparse.Namespace) -> int:
    """Batch process case reports from CSV."""
    import csv
    validator = CARECaseReportValidator()
    with open(args.input, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    generated_fields = ["compliance_score", "compliance_tier", "items_met", "items_total", "timeline_valid", "phi_violations_count"]
    out_fields = fieldnames + [name for name in generated_fields if name not in fieldnames]
    out_rows = []
    for r in rows:
        title = r.get("title") or r.get("case_id") or "Case Report"
        abstract = r.get("abstract") or r.get("summary") or ""
        clinical = r.get("clinical_findings") or r.get("findings") or ""
        timeline = r.get("timeline") or ""
        diag = r.get("diagnostic_assessment") or ""
        tx = r.get("therapeutic_intervention") or ""
        consent = r.get("informed_consent") or ""
        keywords_raw = r.get("keywords") or r.get("key_words") or ""
        keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()] if keywords_raw else []

        payload = {
            "title": title,
            "keywords": keywords,
            "abstract": {"introduction": abstract} if abstract else {},
            "introduction": r.get("introduction") or r.get("background") or "",
            "clinical_findings": clinical,
            "timeline": timeline,
            "diagnostic_assessment": diag,
            "therapeutic_intervention": tx,
            "informed_consent": consent,
        }
        report = validator.validate(payload)
        row_dict = dict(r)
        row_dict["compliance_score"] = f"{report.overall_compliance_score:.1f}%"
        row_dict["compliance_tier"] = report.compliance_tier.value
        row_dict["items_met"] = report.items_met
        row_dict["items_total"] = report.items_total
        row_dict["timeline_valid"] = report.timeline_valid
        row_dict["phi_violations_count"] = len(report.phi_violations)
        out_rows.append(row_dict)

    with open(args.output, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"Processed {len(out_rows)} case reports into '{args.output}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

