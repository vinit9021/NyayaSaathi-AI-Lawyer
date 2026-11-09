from types import SimpleNamespace
from unittest.mock import Mock

from google.genai import errors
import httpx2
import pytest

from nyayasaathi.config import Settings
from nyayasaathi.extraction import EXTRACTION_SCHEMA
from nyayasaathi.llm.base import LLMError, LLMErrorCode
from nyayasaathi.llm.factory import create_llm_client
from nyayasaathi.llm.gemini import GeminiLLM
from nyayasaathi.models import LLMRequest, Message

pytestmark = pytest.mark.offline


@pytest.fixture
def settings():
    return Settings(gemini_api_key="synthetic-only-key", gemini_model="configured-test-model")


@pytest.fixture
def request_data():
    return LLMRequest("Extract only", (Message("user", "fictional input"),), response_schema=EXTRACTION_SCHEMA)


def response(text="{}"):
    return SimpleNamespace(text=text, usage_metadata=SimpleNamespace(prompt_token_count=10, candidates_token_count=5))


def test_maps_official_sdk_request_and_response(settings, request_data):
    sdk = Mock()
    sdk.models.generate_content.return_value = response()
    result = GeminiLLM(settings, sdk_client=sdk).generate(request_data)
    assert result.model == settings.gemini_model and result.usage.input_tokens == 10
    kwargs = sdk.models.generate_content.call_args.kwargs
    assert kwargs["model"] == "configured-test-model"
    assert kwargs["config"].response_json_schema == EXTRACTION_SCHEMA
    assert kwargs["config"].http_options.retry_options.attempts == 1
    assert kwargs["config"].http_options.timeout == 30000
    assert kwargs["config"].automatic_function_calling.disable
    assert kwargs["contents"][0].role == "user"


def test_missing_key_and_model_are_safe(request_data):
    for config, code in [(Settings(), LLMErrorCode.MISSING_CREDENTIALS),
                         (Settings(gemini_api_key="synthetic"), LLMErrorCode.UNAVAILABLE)]:
        with pytest.raises(LLMError) as error:
            GeminiLLM(config).generate(request_data)
        assert error.value.code == code


def test_no_network_without_explicit_permission(settings, request_data, monkeypatch):
    constructor = Mock(side_effect=AssertionError("must not construct SDK"))
    monkeypatch.setattr("nyayasaathi.llm.gemini.genai.Client", constructor)
    with pytest.raises(LLMError):
        GeminiLLM(settings).generate(request_data)
    constructor.assert_not_called()


@pytest.mark.parametrize("error,code,retries", [
    (errors.ClientError(403, {"message": "synthetic private credential"}), LLMErrorCode.AUTHENTICATION, 0),
    (errors.ClientError(400, {"message": "API_KEY_INVALID synthetic private credential"}), LLMErrorCode.AUTHENTICATION, 0),
    (errors.ClientError(429, {"message": "quota"}), LLMErrorCode.QUOTA, 0),
    (errors.ClientError(404, {"message": "model absent"}), LLMErrorCode.INVALID_RESPONSE, 0),
    (errors.ServerError(503, {"message": "unavailable"}), LLMErrorCode.UNAVAILABLE, 1),
    (httpx2.ConnectError("synthetic private request"), LLMErrorCode.UNAVAILABLE, 1),
    (httpx2.ReadTimeout("synthetic private request"), LLMErrorCode.TIMEOUT, 1),
])
def test_normalized_errors_and_bounded_retries(settings, request_data, error, code, retries):
    sdk, sleep = Mock(), Mock()
    sdk.models.generate_content.side_effect = error
    with pytest.raises(LLMError) as caught:
        GeminiLLM(settings, sdk_client=sdk, sleep=sleep).generate(request_data)
    assert caught.value.code == code
    assert sdk.models.generate_content.call_count == 1 + retries
    assert sleep.call_count == retries
    assert "synthetic private" not in str(caught.value)


def test_transient_retry_can_recover(settings, request_data):
    sdk = Mock()
    sdk.models.generate_content.side_effect = [TimeoutError(), response()]
    assert GeminiLLM(settings, sdk_client=sdk, sleep=lambda _: None).generate(request_data).text == "{}"
    assert sdk.models.generate_content.call_count == 2


@pytest.mark.parametrize("text", ["", None, "not json", "[]", "x" * 24001])
def test_invalid_provider_response(settings, request_data, text):
    sdk = Mock()
    sdk.models.generate_content.return_value = response(text)
    with pytest.raises(LLMError) as error:
        GeminiLLM(settings, sdk_client=sdk).generate(request_data)
    assert error.value.code == LLMErrorCode.INVALID_RESPONSE
    assert sdk.models.generate_content.call_count == 1


def test_explicit_live_factory_creates_adapter_not_call(settings, request_data, monkeypatch):
    sdk = Mock()
    sdk.models.generate_content.return_value = response()
    constructor = Mock(return_value=sdk)
    monkeypatch.setattr("nyayasaathi.llm.gemini.genai.Client", constructor)
    client = create_llm_client(settings, allow_live=True)
    constructor.assert_not_called()
    client.generate(request_data)
    assert constructor.call_args.kwargs["api_key"] == "synthetic-only-key"
    sdk.close.assert_called_once_with()
