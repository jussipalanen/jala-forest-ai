"""Streamlit app flow with a fake assistant and a small synthetic GeoParquet file."""

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest
from synthetic import write_synthetic_stands

from jalaforest.assistant import AssistantReply
from jalaforest.search import SearchFilters

APP = str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")


class FakeAssistant:
    model = "fake"

    def __init__(self):
        self.calls = []

    def reply(self, history):
        self.calls.append(history)
        if len(history) == 1:
            return AssistantReply(action="clarify", question="Mitä tarkoitat isoilla kuvioilla?")
        return AssistantReply(action="search", filters=SearchFilters(min_area_ha=2, natura="overlaps"))


@pytest.fixture
def data_path(tmp_path, monkeypatch):
    path = write_synthetic_stands(tmp_path / "stands.parquet")
    monkeypatch.setenv("DATA_PATH", str(path))
    monkeypatch.setenv("AI_ENABLED", "true")
    return path


def _texts(at):
    """Visible text from markdown and st.html blocks (tags stripped)."""
    html = " ".join(e.proto.body for e in at.get("html") if not e.proto.body.startswith(("<style", "<script")))
    text = " ".join([*(m.value for m in at.markdown), re.sub(r"<[^>]+>", " ", html)])
    return re.sub(r"\s+", " ", text)


def test_clarify_then_search(data_path):
    at = AppTest.from_file(APP, default_timeout=60)
    fake = FakeAssistant()
    at.session_state["assistant"] = fake
    at.run()
    assert not at.exception
    assert "4 kuviota" in _texts(at) and "Kaikki kuviot" in _texts(at)

    at.chat_input[0].set_value("Etsi isot metsäkuviot, jotka osuvat Natura 2000 -alueelle").run()
    assert not at.exception
    assert "Tarkentava kysymys" in _texts(at) and "Mitä tarkoitat isoilla kuvioilla?" in _texts(at)

    at.chat_input[0].set_value("Yli kaksi hehtaaria").run()
    assert not at.exception
    text = _texts(at)
    # Only stand 1: stand 2 is outside Natura, stand 3 is too small, stand 4 is a sliver.
    assert "Löytyi 1 kuvio, yhteensä 3 ha." in text
    assert "pinta-ala vähintään 2 ha" in text and "osuu Natura 2000 -alueelle" in text
    assert at.number_input[0].value == 2
    assert at.radio[0].value == "overlaps"
    assert [t["role"] for t in fake.calls[-1]] == ["user", "model", "user"]


def test_empty_result_shows_zero(data_path):
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["assistant"] = FakeAssistant()
    at.run()
    at.number_input[0].set_value(100.0).run()
    assert not at.exception
    assert "Hakuehdoilla ei löytynyt yhtään kuviota." in _texts(at)


def test_ai_disabled_by_env(data_path, monkeypatch):
    monkeypatch.setenv("AI_ENABLED", "false")
    at = AppTest.from_file(APP, default_timeout=60)
    fake = FakeAssistant()
    at.session_state["assistant"] = fake
    at.run()
    assert not at.exception
    assert at.chat_input[0].disabled
    assert fake.calls == []
