import os
from unittest.mock import Mock

import pytest
from streamlit.errors import StreamlitSecretNotFoundError

from nyayasaathi.config import (
    ConfigurationError, Settings, load_settings, load_streamlit_settings,
)

pytestmark = pytest.mark.offline


def test_defaults_need_no_keys():
    settings = load_settings(environ={})
    assert settings == Settings()
    assert settings.gemini_api_key is None
    assert settings.groq_api_key is None
    with pytest.raises(ConfigurationError, match="GEMINI_API_KEY, GEMINI_MODEL"):
        settings.require_gemini()
    with pytest.raises(ConfigurationError, match="GROQ_API_KEY"):
        settings.require_groq()


@pytest.mark.parametrize("timeout", [30, 60, 90])
def test_supported_timeout_bounds(timeout):
    assert load_settings(environ={"LLM_TIMEOUT_SECONDS": str(timeout)}).llm_timeout_seconds == timeout


def test_precedence_and_no_process_mutation(tmp_path):
    path = tmp_path / ".env"
    path.write_text("GEMINI_API_KEY=synthetic-dotenv\nGEMINI_MODEL=local-model\nGROQ_API_KEY=synthetic-voice\n", encoding="utf-8")
    before = dict(os.environ)
    settings = load_settings(
        environ={"GEMINI_API_KEY": "synthetic-environment"},
        secrets={"GEMINI_API_KEY": "synthetic-secrets", "GEMINI_MODEL": "hosted-model"},
        dotenv_path=path,
    )
    assert settings.gemini_api_key == "synthetic-environment"
    assert settings.gemini_model == "hosted-model"
    assert settings.groq_api_key == "synthetic-voice"
    assert dict(os.environ) == before
    settings.require_gemini()
    settings.require_groq()


def test_blank_environment_disables_lower_priority_key():
    settings = load_settings(environ={"GEMINI_API_KEY": " "}, secrets={"GEMINI_API_KEY": "synthetic-secret"})
    assert settings.gemini_api_key is None


def test_dotenv_is_opt_in_and_not_interpolated(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text("GEMINI_API_KEY=${UNRELATED_SECRET}\n", encoding="utf-8")
    monkeypatch.setenv("UNRELATED_SECRET", "synthetic-not-for-provider")
    assert load_settings(environ={}).gemini_api_key is None
    assert load_settings(environ={}, dotenv_path=path).gemini_api_key == "${UNRELATED_SECRET}"
    assert load_settings(environ={}, dotenv_path=tmp_path / "absent").gemini_api_key is None


@pytest.mark.parametrize("name,value", [
    ("LLM_TIMEOUT_SECONDS", "0"), ("LLM_TIMEOUT_SECONDS", "91"),
    ("LLM_TIMEOUT_SECONDS", "not-a-number"), ("LLM_MAX_RETRIES", "2"),
    ("LLM_MAX_RETRIES", "-1"), ("LLM_MAX_OUTPUT_TOKENS", "0"),
    ("LLM_MAX_OUTPUT_TOKENS", "8193"), ("LLM_PROVIDER", ""),
    ("GEMINI_API_KEY", {"nested": "synthetic-sensitive-value"}),
    ("LLM_TIMEOUT_SECONDS", True),
])
def test_invalid_settings_fail_without_value_disclosure(name, value):
    with pytest.raises(ConfigurationError) as caught:
        load_settings(environ={}, secrets={name: value})
    assert name in str(caught.value)
    assert "synthetic-sensitive-value" not in str(caught.value)


def test_direct_settings_validation():
    with pytest.raises(ConfigurationError):
        Settings(llm_max_retries=2)
    with pytest.raises(ConfigurationError):
        Settings(gemini_api_key=123)


def test_toml_integer_values_and_secret_repr():
    settings = load_settings(environ={}, secrets={
        "LLM_TIMEOUT_SECONDS": 15, "LLM_MAX_RETRIES": 0,
        "GEMINI_API_KEY": "synthetic-private-key", "GROQ_API_KEY": "synthetic-voice-key",
    })
    assert settings.llm_timeout_seconds == 15
    assert settings.llm_max_retries == 0
    assert "synthetic-private-key" not in repr(settings)
    assert "synthetic-voice-key" not in repr(settings)


def test_streamlit_secrets_injection():
    loader = Mock(return_value={"GEMINI_MODEL": "test-model", "GEMINI_API_KEY": "synthetic-key"})
    settings = load_streamlit_settings(secrets_loader=loader)
    assert settings.gemini_model == "test-model"
    settings.require_gemini()
    loader.assert_called_once_with()


@pytest.mark.parametrize("error", [
    FileNotFoundError(),
    StreamlitSecretNotFoundError("missing", error_id="no-secrets-found"),
])
def test_missing_streamlit_secrets_are_optional(error):
    settings = load_streamlit_settings(secrets_loader=Mock(side_effect=error))
    assert settings == Settings()


def test_streamlit_errors_do_not_expose_content():
    with pytest.raises(ConfigurationError) as caught:
        load_streamlit_settings(secrets_loader=Mock(side_effect=ValueError("synthetic-private-key")))
    assert "synthetic-private-key" not in str(caught.value)


def test_malformed_streamlit_file_is_not_treated_as_absent():
    error = StreamlitSecretNotFoundError(
        "synthetic-private-key", error_id="failed-parsing-secrets-file",
    )
    with pytest.raises(ConfigurationError) as caught:
        load_streamlit_settings(secrets_loader=Mock(side_effect=error))
    assert "synthetic-private-key" not in str(caught.value)


def test_environment_precedes_streamlit_side_effect(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "synthetic-environment")

    def loader():
        monkeypatch.setenv("GEMINI_API_KEY", "synthetic-hosted")
        return {"GEMINI_API_KEY": "synthetic-hosted"}

    assert load_streamlit_settings(secrets_loader=loader).gemini_api_key == "synthetic-environment"


def test_real_streamlit_loader_uses_only_mocked_secrets(monkeypatch):
    import streamlit as st
    secrets = Mock()
    secrets.to_dict.return_value = {"GEMINI_MODEL": "synthetic-model"}
    monkeypatch.setattr(st, "secrets", secrets)
    assert load_streamlit_settings().gemini_model == "synthetic-model"
    secrets.to_dict.assert_called_once_with()
