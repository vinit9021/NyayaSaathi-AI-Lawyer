from types import SimpleNamespace
from dataclasses import replace
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime
from unittest.mock import Mock

from google.genai import errors
import httpx2
import pytest

from nyayasaathi.config import Settings
from nyayasaathi.extraction import EXTRACTION_SCHEMA
from nyayasaathi.llm.base import LLMError, LLMErrorCode
from nyayasaathi.llm.factory import create_llm_client
from nyayasaathi.llm.gemini import GeminiLLM
from nyayasaathi.llm.gemini import _retry_delay
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


def api_failure(code, *, header=None, details=None, message="temporary"):
    response = httpx2.Response(code, headers={} if header is None else {"Retry-After": header})
    return errors.APIError(code, {"error": {"message": message, "details": details or []}}, response)


@pytest.mark.parametrize("code", [429, 500, 502, 503, 504])
def test_retry_after_respected_and_success_does_not_duplicate(settings, request_data, code):
    sdk, sleep = Mock(), Mock()
    sdk.models.generate_content.side_effect = [api_failure(code, header="3"), response()]
    result = GeminiLLM(settings, sdk_client=sdk, sleep=sleep, jitter=lambda: 0).generate(request_data)
    assert result.text == "{}"
    sleep.assert_called_once_with(3.0)
    assert sdk.models.generate_content.call_count == 2


@pytest.mark.parametrize("failure", [
    api_failure(401), api_failure(403), api_failure(400), api_failure(429),
    api_failure(429, header="2", message="Daily quota exhausted"),
    api_failure(429, header="2", message="Quota exceeded"),
    api_failure(429, header="2", details=[{"@type": "google.rpc.QuotaFailure", "violations": [{"quotaId": "RequestsPerDay"}]}]),
    api_failure(429, header="2", details=[{"@type": "google.rpc.QuotaFailure", "violations": [{"quotaId": "RequestsPerMinute", "quotaValue": "0"}]}]),
    api_failure(503, header="61"), api_failure(503, header="bad"), api_failure(503, header="NaN"),
    api_failure(501),
    api_failure(429, header="2", details=[{"@type": "google.rpc.QuotaFailure", "violations": None}]),
])
def test_no_blind_retry_or_shortening_provider_wait(settings, request_data, failure):
    sdk, sleep = Mock(), Mock()
    sdk.models.generate_content.side_effect = failure
    with pytest.raises(LLMError):
        GeminiLLM(settings, sdk_client=sdk, sleep=sleep).generate(request_data)
    assert sdk.models.generate_content.call_count == 1
    sleep.assert_not_called()


def test_retry_info_and_exponential_jitter():
    failure = api_failure(503)
    assert _retry_delay(failure, 0, lambda: 0.5) == 0.75
    assert _retry_delay(failure, 1, lambda: 0.5) == 1.5
    rate_limit = api_failure(429, details=[{"@type": "google.rpc.RetryInfo", "retryDelay": "4.5s"}])
    assert _retry_delay(rate_limit, 0, lambda: 0) == 4.5
    dated = api_failure(503, header=format_datetime(datetime.now(timezone.utc) + timedelta(seconds=10), usegmt=True))
    assert 8 <= _retry_delay(dated, 0, lambda: 0) <= 10


def test_explicit_zero_retries_and_90_second_timeout(settings, request_data):
    sdk, sleep = Mock(), Mock()
    sdk.models.generate_content.side_effect = api_failure(503, header="2")
    with pytest.raises(LLMError):
        GeminiLLM(replace(settings, llm_max_retries=0, llm_timeout_seconds=90), sdk_client=sdk, sleep=sleep).generate(request_data)
    assert sdk.models.generate_content.call_count == 1
    assert sdk.models.generate_content.call_args.kwargs['config'].http_options.timeout == 90000
    sleep.assert_not_called()


def test_retry_keeps_one_case_turn_and_preserves_confirmed_facts(settings):
    from datetime import date
    from nyayasaathi.conversation import process_turn
    from nyayasaathi.extraction import confirm_fact
    from nyayasaathi.models import CaseState
    from nyayasaathi.retrieval import load_catalogue
    sdk = Mock()
    sdk.models.generate_content.side_effect = [api_failure(503), response('{"topic":"consumer","confidence":1,"risk_flags":[],"facts":[]}')]
    client = GeminiLLM(settings, sdk_client=sdk, sleep=lambda _: None)
    original = confirm_fact(CaseState(topic='consumer'), 'amount_paid', '3500')
    result = process_turn(original, 'online refund', 'one', client, load_catalogue(), as_of=date(2026,11,10))
    assert result.facts == original.facts
    assert len(result.history) == len(original.history) + 2
    assert result.processed_ids == ('one',)
    assert process_turn(result, 'online refund', 'one', client, load_catalogue()) is result
    assert sdk.models.generate_content.call_count == 2
