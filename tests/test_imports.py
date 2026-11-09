import importlib
from pathlib import Path
import tomllib
from unittest.mock import Mock

import pytest

pytestmark = pytest.mark.offline
ROOT = Path(__file__).resolve().parents[1]


def test_all_modules_import_without_provider_clients(monkeypatch):
    from google import genai
    import groq

    forbidden = Mock(side_effect=AssertionError("SDK client must not be constructed"))
    monkeypatch.setattr(genai, "Client", forbidden)
    monkeypatch.setattr(groq, "Groq", forbidden)
    for module in (
        "app", "nyayasaathi.config", "nyayasaathi.models", "nyayasaathi.conversation",
        "nyayasaathi.extraction", "nyayasaathi.retrieval", "nyayasaathi.safety",
        "nyayasaathi.drafting", "nyayasaathi.speech", "nyayasaathi.llm.base",
        "nyayasaathi.llm.factory", "nyayasaathi.llm.gemini",
    ):
        importlib.import_module(module)
    forbidden.assert_not_called()


def test_project_and_streamlit_configuration_parse():
    with (ROOT / "pyproject.toml").open("rb") as file:
        assert tomllib.load(file)["project"]["requires-python"] == ">=3.12,<3.13"
    with (ROOT / ".streamlit" / "config.toml").open("rb") as file:
        assert tomllib.load(file)["browser"]["gatherUsageStats"] is False


def test_foundation_entrypoint_renders_without_keys():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(ROOT / "app.py")).run()
    assert not app.exception
    assert app.title[0].value == "NyayaSaathi"
    assert "not available yet" in app.info[0].value
    assert len(app.chat_input) == 0
