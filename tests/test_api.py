from __future__ import annotations

from fastapi.testclient import TestClient

from src.medical_triage_system.web_app import app

client = TestClient(app)

VALID_CASE = {
    "age": "21",
    "sex": "female",
    "vitals": "Temp 38.3C, HR 108",
    "symptoms": "Fever, sore throat",
    "model_profile": "model_1",
    "prompt_set": "default",
}


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_options_lists_profiles_and_prompt_sets():
    body = client.get("/api/options").json()
    assert {"model_1", "model_2", "model_3", "model_4"} <= set(body["model_profiles"])
    assert "default" in body["prompt_sets"]


def test_index_page_renders():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_analyze_rejects_missing_required_fields():
    response = client.post("/api/analyze", json={"age": "30"})
    assert response.status_code == 422


def test_analyze_rejects_empty_symptoms():
    response = client.post("/api/analyze", json={**VALID_CASE, "symptoms": ""})
    assert response.status_code == 422


def test_analyze_returns_all_four_reports(fake_llm):
    response = client.post("/api/analyze", json=VALID_CASE)
    assert response.status_code == 200

    body = response.json()
    assert body["model_profile"] == "model_1"
    assert set(body["reports"]) == {"intake", "triage", "diagnosis", "treatment"}
    assert all(value >= 0 for value in body["durations"].values())


def test_analyze_unknown_profile_returns_500(fake_llm):
    response = client.post("/api/analyze", json={**VALID_CASE, "model_profile": "does_not_exist"})
    assert response.status_code == 500
    assert "Unknown model profile" in response.json()["detail"]
