"""Minimal synchronous contract; SDK types and raw exceptions stay in adapters."""

from enum import StrEnum
from typing import Protocol, runtime_checkable

from nyayasaathi.models import LLMRequest, LLMResponse


class LLMErrorCode(StrEnum):
    MISSING_CREDENTIALS = "missing_credentials"
    AUTHENTICATION = "authentication"
    QUOTA = "quota"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    INVALID_RESPONSE = "invalid_response"


_MESSAGES = {
    LLMErrorCode.MISSING_CREDENTIALS: "Configure the provider key in private settings.",
    LLMErrorCode.AUTHENTICATION: "Provider authentication failed. Check private settings.",
    LLMErrorCode.QUOTA: "Provider quota is unavailable. Check usage before trying again.",
    LLMErrorCode.TIMEOUT: "The model request timed out. Please try again later.",
    LLMErrorCode.UNAVAILABLE: "The model provider is unavailable or not integrated yet.",
    LLMErrorCode.INVALID_RESPONSE: "The model returned an invalid response. Please try again.",
}


class LLMError(Exception):
    def __init__(self, code: LLMErrorCode):
        if not isinstance(code, LLMErrorCode):
            raise ValueError("A normalized LLMErrorCode is required.")
        self.code = code
        super().__init__(_MESSAGES[code])

    @property
    def retryable(self) -> bool:
        return self.code in (LLMErrorCode.TIMEOUT, LLMErrorCode.UNAVAILABLE)


@runtime_checkable
class LLMClient(Protocol):
    def generate(self, request: LLMRequest) -> LLMResponse:
        """Return a neutral response or raise LLMError, never a raw SDK error.

        Implementations must honor configured timeout/retry bounds, avoid logging
        content, and validate response shape. No tools or side effects beyond
        generation. Legal grounding is the caller's responsibility.
        """
        ...
