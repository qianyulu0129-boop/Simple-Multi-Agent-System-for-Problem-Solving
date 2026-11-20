from __future__ import annotations

import pytest

from src.medical_triage_system import coordinator as coordinator_module


class FakeLLMClient:
    """Stands in for the real OpenAI-compatible client so tests never hit the network."""

    instances: list["FakeLLMClient"] = []

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.calls: list[dict] = []
        FakeLLMClient.instances.append(self)

    def generate(self, model: str, system_prompt: str, user_prompt: str) -> str:
        self.calls.append({"model": model, "system_prompt": system_prompt, "user_prompt": user_prompt})
        return f"[stage {len(self.calls)}] output from {model}"


@pytest.fixture
def fake_llm(monkeypatch, tmp_path):
    FakeLLMClient.instances.clear()
    monkeypatch.setattr(coordinator_module, "LLMClient", FakeLLMClient)
    monkeypatch.setenv("PROVIDER_1_API_KEY", "test-key")
    monkeypatch.setenv("PROVIDER_1_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("OUTPUT_ROOT", str(tmp_path / "outputs"))
    return FakeLLMClient
