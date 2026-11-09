"""Test-only scripted provider; never registered by production code."""

from collections import deque

from nyayasaathi.llm.base import LLMError, LLMErrorCode
from nyayasaathi.models import LLMRequest, LLMResponse


class FakeLLM:
    def __init__(self, *results: LLMResponse | LLMError):
        self.results = deque(results)
        self.requests: list[LLMRequest] = []

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        if not self.results:
            raise LLMError(LLMErrorCode.UNAVAILABLE)
        result = self.results.popleft()
        if isinstance(result, LLMError):
            raise result
        return result
