from __future__ import annotations

from eval.metrics import score_case_result
from eval.parsers import compute_macro_f1, parse_predicted_urgency, section_coverage

OPTIONS = {
    "A": "Streptococcal pharyngitis",
    "B": "Infectious mononucleosis",
    "C": "Peritonsillar abscess",
}


def make_row(diagnosis_output: str) -> dict:
    return {
        "options": OPTIONS,
        "gold_answer_idx": "B",
        "gold_answer_text": "Infectious mononucleosis",
        "intake_output": "Patient summary",
        "triage_output": "Urgency level",
        "diagnosis_output": diagnosis_output,
        "treatment_output": "",
        "intake_duration_seconds": 1.0,
        "triage_duration_seconds": 2.0,
        "diagnosis_duration_seconds": 3.0,
        "treatment_duration_seconds": 4.0,
    }


def test_top1_hit_when_gold_answer_ranked_first():
    scored = score_case_result(make_row("Infectious mononucleosis is most likely, then peritonsillar abscess."))
    assert scored["predicted_top1_option"] == "B"
    assert scored["diagnosis_top1_accuracy"] == 1.0
    assert scored["diagnosis_top3_accuracy"] == 1.0
    assert scored["average_agent_latency"] == 2.5


def test_top3_hit_but_top1_miss():
    scored = score_case_result(make_row("Peritonsillar abscess first; infectious mononucleosis second."))
    assert scored["predicted_top1_option"] == "C"
    assert scored["diagnosis_top1_accuracy"] == 0.0
    assert scored["diagnosis_top3_accuracy"] == 1.0


def test_section_coverage_counts_expected_headings():
    text = "## Urgency level\n...\n## Red-flag findings\n..."
    assert section_coverage(text, "triage") == 2 / 6


def test_urgency_parsing_falls_back_to_esi():
    assert parse_predicted_urgency("Urgency level: Emergency now") == "emergency now"
    assert parse_predicted_urgency("ESI level 4") == "routine medical follow-up"


def test_macro_f1_perfect_predictions():
    labels = ["emergency now", "urgent same-day evaluation", "routine medical follow-up", "self-care with monitoring"]
    assert compute_macro_f1(labels, labels) == 1.0
