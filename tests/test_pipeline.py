from __future__ import annotations

import json

import pytest

from src.medical_triage_system.coordinator import MedicalTriageCoordinator, resolve_provider_config
from src.medical_triage_system.schemas import PatientCase
from src.medical_triage_system.settings_loader import render_prompt


def make_case() -> PatientCase:
    return PatientCase(
        age="21",
        sex="female",
        vitals="Temp 38.3C",
        symptoms="Fever, sore throat",
        medical_history="not provided",
        current_medications="not provided",
        allergies="Penicillin",
        duration="3 days",
    )


def test_render_prompt_substitutes_placeholders():
    assert render_prompt("Case: {{patient_case}}", patient_case="fever") == "Case: fever"


def test_env_vars_override_file_config(monkeypatch):
    monkeypatch.setenv("PROVIDER_9_API_KEY", "from-env")
    merged = resolve_provider_config("provider_9", {"api_key": "from-file", "base_url": "https://file"})
    assert merged == {"api_key": "from-env", "base_url": "https://file"}


def test_missing_provider_returns_none(monkeypatch):
    monkeypatch.delenv("PROVIDER_9_API_KEY", raising=False)
    assert resolve_provider_config("provider_9", None) is None


def test_placeholder_api_key_is_rejected(monkeypatch):
    monkeypatch.delenv("PROVIDER_1_API_KEY", raising=False)
    with pytest.raises(ValueError, match="missing a real API key"):
        MedicalTriageCoordinator(model_profile_name="model_1", prompt_set_name="default")


def test_pipeline_runs_four_stages_in_order_and_passes_context(fake_llm):
    coordinator = MedicalTriageCoordinator(model_profile_name="model_1", prompt_set_name="default")
    artifacts, run_dir = coordinator.run(make_case())

    calls = fake_llm.instances[0].calls
    assert len(calls) == 4
    assert artifacts.intake_report.output_text.startswith("[stage 1]")
    assert artifacts.treatment_report.output_text.startswith("[stage 4]")

    # Each downstream agent should see the outputs of the agents before it.
    assert "[stage 1]" in calls[1]["user_prompt"]
    assert "[stage 2]" in calls[2]["user_prompt"]
    assert "[stage 3]" in calls[3]["user_prompt"]


def test_pipeline_writes_traceable_artifacts(fake_llm):
    coordinator = MedicalTriageCoordinator(model_profile_name="model_1", prompt_set_name="default")
    _, run_dir = coordinator.run(make_case())

    expected = {
        "01_intake_report.md",
        "02_triage_report.md",
        "03_diagnosis_report.md",
        "04_final_report.md",
        "pipeline_summary.json",
    }
    assert expected <= {path.name for path in run_dir.iterdir()}

    summary = json.loads((run_dir / "pipeline_summary.json").read_text(encoding="utf-8"))
    assert summary["triage_report"]["model"] == "google/gemma-4-31b-it"
