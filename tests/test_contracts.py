from dataclasses import FrozenInstanceError, asdict
import json

import pytest

from nyayasaathi.config import ConfigurationError, Settings
from nyayasaathi.llm.base import LLMClient, LLMError, LLMErrorCode
from nyayasaathi.llm.factory import create_llm_client
from nyayasaathi.models import LLMRequest, LLMResponse, Message, TokenUsage
from tests.fakes import FakeLLM

pytestmark = pytest.mark.offline


@pytest.fixture
def llm_request():
    return LLMRequest("Extract facts only.", (Message("user", "मेरा refund nahi mila"),))


def test_fake_obeys_provider_neutral_contract(llm_request):
    response = LLMResponse('{"topic":"unclear"}', "synthetic-model", TokenUsage(4, 3))
    client = FakeLLM(response)
    assert isinstance(client, LLMClient)
    assert client.generate(llm_request) is response
    assert client.requests == [llm_request]
    assert json.loads(json.dumps(asdict(llm_request)))["messages"][0]["content"] == "मेरा refund nahi mila"
    assert json.loads(json.dumps(asdict(response)))["usage"]["input_tokens"] == 4


@pytest.mark.parametrize("provider", ["gemini", "replacement"])
def test_provider_replacement_does_not_change_caller(llm_request, provider):
    response = LLMResponse("{}", "test-model")
    received = []

    def build(settings):
        received.append(settings)
        return FakeLLM(response)

    settings = Settings(llm_provider=provider, gemini_model="test-model")
    client = create_llm_client(settings, builders={provider: build})
    assert client.generate(llm_request) is response
    assert received == [settings]


def test_no_implicit_production_fake():
    with pytest.raises(LLMError) as caught:
        create_llm_client(Settings())
    assert caught.value.code == LLMErrorCode.UNAVAILABLE


def test_factory_rejects_invalid_adapter():
    with pytest.raises(ConfigurationError):
        create_llm_client(Settings(), builders={"gemini": lambda _: object()})


@pytest.mark.parametrize("code", list(LLMErrorCode))
def test_normalized_failures_pass_through_fake(llm_request, code):
    client = FakeLLM(LLMError(code))
    with pytest.raises(LLMError) as caught:
        client.generate(llm_request)
    assert caught.value.code == code
    assert caught.value.retryable == (code in (LLMErrorCode.TIMEOUT, LLMErrorCode.UNAVAILABLE))
    assert str(caught.value)


def test_request_immutable_and_repr_omits_content(llm_request):
    with pytest.raises(FrozenInstanceError):
        llm_request.max_output_tokens = 10
    assert "refund" not in repr(llm_request)
    assert "refund" not in repr(llm_request.messages[0])
    assert "synthetic-private-text" not in repr(LLMResponse("synthetic-private-text", "test"))


@pytest.mark.parametrize("builder", [
    lambda: Message("system", "text"), lambda: Message("user", ""),
    lambda: Message("user", None), lambda: LLMRequest("", (Message("user", "x"),)),
    lambda: LLMRequest("x", ()), lambda: LLMRequest("x", [Message("user", "x")]),
    lambda: LLMRequest("x", (object(),)),
    lambda: LLMRequest("x", (Message("user", "x"),), max_output_tokens=True),
    lambda: LLMRequest("x", (Message("user", "x"),), response_format="xml"),
    lambda: LLMResponse("", "model"), lambda: LLMResponse("x", ""),
    lambda: LLMResponse("x", "model", usage={}),
    lambda: TokenUsage(input_tokens=-1), lambda: TokenUsage(output_tokens=True),
])
def test_malformed_contracts_rejected(builder):
    with pytest.raises(ValueError):
        builder()


def test_unknown_usage_is_not_reported_as_zero():
    assert TokenUsage().input_tokens is None
    assert TokenUsage().output_tokens is None
