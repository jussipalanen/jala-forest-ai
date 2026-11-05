"""Gemini reply parsing and validation with a fake client (no network)."""

import json
from types import SimpleNamespace

import pytest

from jalaforest.assistant import Assistant, AssistantError, AssistantUnavailable, ai_enabled


class FakeModels:
    def __init__(self, texts):
        self.texts = list(texts)
        self.requests = []

    def generate_content(self, **kwargs):
        self.requests.append(kwargs)
        text = self.texts.pop(0)
        if isinstance(text, Exception):
            raise text
        return SimpleNamespace(text=text)


def fake_assistant(*texts):
    models = FakeModels(texts)
    return Assistant(client=SimpleNamespace(models=models), model="test-model"), models


def test_clarify_then_search_keeps_history():
    clarify = json.dumps({"action": "clarify", "question": "Mitä tarkoitat isoilla kuvioilla?"})
    search = json.dumps({"action": "search", "filters": {"min_area_ha": 2, "natura": "overlaps"}})
    assistant, models = fake_assistant(clarify, search)

    history = [{"role": "user", "text": "Etsi isot metsäkuviot, jotka osuvat Natura 2000 -alueelle"}]
    first = assistant.reply(history)
    assert first.action == "clarify" and first.question

    history += [{"role": "model", "text": first.question}, {"role": "user", "text": "Yli kaksi hehtaaria"}]
    second = assistant.reply(history)
    assert second.filters.min_area_ha == 2 and second.filters.natura == "overlaps"

    sent = models.requests[-1]
    assert [c["role"] for c in sent["contents"]] == ["user", "model", "user"]
    assert sent["model"] == "test-model"
    assert sent["config"]["response_mime_type"] == "application/json"
    assert "properties" in sent["config"]["response_json_schema"]


@pytest.mark.parametrize("text", [
    "not json",
    json.dumps({"action": "search"}),                                         # filters missing
    json.dumps({"action": "clarify", "question": " "}),                       # empty question
    json.dumps({"action": "search", "filters": {"min_area_ha": -1}}),         # negative area
    json.dumps({"action": "search", "filters": {"min_area_ha": 5, "max_area_ha": 1}}),
])
def test_invalid_model_output_is_rejected(text):
    assistant, _ = fake_assistant(text)
    with pytest.raises(AssistantError, match="tulkinta epäonnistui"):
        assistant.reply([{"role": "user", "text": "x"}])


def test_api_error_is_reported_in_finnish():
    assistant, _ = fake_assistant(RuntimeError("503"))
    with pytest.raises(AssistantError, match="Hakupalvelu ei vastannut"):
        assistant.reply([{"role": "user", "text": "x"}])


class Overloaded(Exception):
    code = 503


def test_overload_falls_back_to_next_cheapest_model():
    ok = json.dumps({"action": "clarify", "question": "Mitä tarkoitat?"})
    models = FakeModels([Overloaded("503 UNAVAILABLE"), ok])
    assistant = Assistant(client=SimpleNamespace(models=models), model="cheap", fallback_model="next")
    assert assistant.reply([{"role": "user", "text": "x"}]).action == "clarify"
    assert [r["model"] for r in models.requests] == ["cheap", "next"]


def test_overload_on_both_models_is_a_clear_error():
    models = FakeModels([Overloaded("503"), Overloaded("503")])
    assistant = Assistant(client=SimpleNamespace(models=models), model="cheap", fallback_model="next")
    with pytest.raises(AssistantError, match="ruuhkautunut"):
        assistant.reply([{"role": "user", "text": "x"}])


def test_other_errors_do_not_use_fallback():
    models = FakeModels([RuntimeError("400 bad request")])
    assistant = Assistant(client=SimpleNamespace(models=models), model="cheap", fallback_model="next")
    with pytest.raises(AssistantError, match="ei vastannut"):
        assistant.reply([{"role": "user", "text": "x"}])
    assert [r["model"] for r in models.requests] == ["cheap"]


def test_missing_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(AssistantUnavailable, match="GEMINI_API_KEY"):
        Assistant().reply([{"role": "user", "text": "x"}])


@pytest.mark.parametrize("value,expected", [
    (None, True), ("true", True), ("1", True), ("ON", True),
    ("false", False), ("0", False), ("no", False), (" off ", False),
])
def test_ai_enabled_switch(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv("AI_ENABLED", raising=False)
    else:
        monkeypatch.setenv("AI_ENABLED", value)
    assert ai_enabled() is expected


def test_ai_enabled_rejects_unknown_value(monkeypatch):
    monkeypatch.setenv("AI_ENABLED", "maybe")
    with pytest.raises(ValueError, match="AI_ENABLED"):
        ai_enabled()
