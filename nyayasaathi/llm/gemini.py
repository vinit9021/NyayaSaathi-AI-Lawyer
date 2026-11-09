"""Google Gen AI adapter. No SDK client or request is created on import."""

import json
import time
from collections.abc import Callable

from google import genai
from google.genai import errors, types
import httpx
import httpx2

from nyayasaathi.config import Settings
from nyayasaathi.llm.base import LLMError, LLMErrorCode
from nyayasaathi.models import LLMRequest, LLMResponse, TokenUsage


class GeminiLLM:
    def __init__(self, settings: Settings, *, allow_live: bool = False,
                 sdk_client=None, sleep: Callable[[float], None] = time.sleep):
        self.settings = settings
        self.allow_live = allow_live
        self._injected = sdk_client
        self._sleep = sleep

    def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.settings.gemini_api_key:
            raise LLMError(LLMErrorCode.MISSING_CREDENTIALS)
        if not self.settings.gemini_model:
            raise LLMError(LLMErrorCode.UNAVAILABLE)
        if self._injected is None and not self.allow_live:
            raise LLMError(LLMErrorCode.UNAVAILABLE)
        options = types.HttpOptions(
            timeout=self.settings.llm_timeout_seconds * 1000,
            retry_options=types.HttpRetryOptions(attempts=1),  # Retry only here, never twice.
        )
        client = self._injected
        try:
            if client is None:
                client = genai.Client(api_key=self.settings.gemini_api_key, http_options=options)
            config = types.GenerateContentConfig(
                system_instruction=request.system_instruction,
                response_mime_type="application/json" if request.response_format == "json" else "text/plain",
                response_json_schema=request.response_schema,
                max_output_tokens=min(request.max_output_tokens, self.settings.llm_max_output_tokens),
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                http_options=options,
            )
            contents = [types.Content(role="user" if m.role == "user" else "model",
                                      parts=[types.Part.from_text(text=m.content)]) for m in request.messages]
            for attempt in range(self.settings.llm_max_retries + 1):
                try:
                    raw = client.models.generate_content(model=self.settings.gemini_model, contents=contents, config=config)
                    text = raw.text
                    if not isinstance(text, str) or not text.strip() or len(text) > 24000:
                        raise LLMError(LLMErrorCode.INVALID_RESPONSE)
                    if request.response_format == "json":
                        try:
                            if not isinstance(json.loads(text), dict):
                                raise ValueError
                        except (ValueError, TypeError, RecursionError):
                            raise LLMError(LLMErrorCode.INVALID_RESPONSE) from None
                    usage = raw.usage_metadata
                    return LLMResponse(text, self.settings.gemini_model, TokenUsage(
                        input_tokens=getattr(usage, "prompt_token_count", None),
                        output_tokens=getattr(usage, "candidates_token_count", None),
                    ))
                except LLMError:
                    raise
                except Exception as exc:
                    code = _error_code(exc)
                    if code in {LLMErrorCode.TIMEOUT, LLMErrorCode.UNAVAILABLE} and attempt < self.settings.llm_max_retries:
                        self._sleep(0.5 * (2 ** attempt))
                        continue
                    raise LLMError(code) from None
        except LLMError:
            raise
        except Exception:
            raise LLMError(LLMErrorCode.UNAVAILABLE) from None
        finally:
            if client is not None and self._injected is None:
                try:
                    client.close()
                except Exception:
                    pass  # Cleanup errors must not expose request/credential material.


def _error_code(exc: Exception) -> LLMErrorCode:
    if isinstance(exc, (TimeoutError, httpx.TimeoutException, httpx2.TimeoutException)):
        return LLMErrorCode.TIMEOUT
    if isinstance(exc, (ConnectionError, httpx.TransportError, httpx2.TransportError)):
        return LLMErrorCode.UNAVAILABLE
    if isinstance(exc, errors.APIError):
        if exc.code in (401, 403) or (exc.code == 400 and "API_KEY_INVALID" in str(exc.details)):
            return LLMErrorCode.AUTHENTICATION
        if exc.code == 429:
            return LLMErrorCode.QUOTA  # No automatic retry of possibly exhausted quota.
        if exc.code in (408, 504):
            return LLMErrorCode.TIMEOUT
        if exc.code >= 500:
            return LLMErrorCode.UNAVAILABLE
    return LLMErrorCode.INVALID_RESPONSE
