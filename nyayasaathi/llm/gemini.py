"""Google Gen AI adapter. No SDK client or request is created on import."""

import json
import time
import math
import random
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
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
                 sdk_client=None, sleep: Callable[[float], None] = time.sleep,
                 jitter: Callable[[], float] = random.random):
        self.settings = settings
        self.allow_live = allow_live
        self._injected = sdk_client
        self._sleep = sleep
        self._jitter = jitter

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
                    candidates = getattr(raw, "candidates", None)
                    if isinstance(candidates, list):
                        if len(candidates) != 1 or candidates[0].finish_reason != types.FinishReason.STOP:
                            # Never salvage partial JSON or safety-filtered output,
                            # even if its text happens to be syntactically valid.
                            raise LLMError(LLMErrorCode.INVALID_RESPONSE)
                    text = raw.text
                    if not isinstance(text, str) or not text.strip() or len(text) > 24000:
                        raise LLMError(LLMErrorCode.INVALID_RESPONSE)
                    if request.response_format == "json":
                        # One bounded local repair: remove only a complete JSON
                        # fence/BOM. Never guess missing braces or make a repair call.
                        text = text.lstrip('\ufeff').strip()
                        fenced = re.fullmatch(r'```(?:json)?\s*\n(.*?)\n```', text, re.S)
                        if fenced:
                            text = fenced.group(1).strip()
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
                    delay = _retry_delay(exc, attempt, self._jitter)
                    if delay is not None and attempt < self.settings.llm_max_retries:
                        self._sleep(delay)
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
            return LLMErrorCode.QUOTA
        if exc.code in (408, 504):
            return LLMErrorCode.TIMEOUT
        if exc.code >= 500:
            return LLMErrorCode.UNAVAILABLE
    return LLMErrorCode.INVALID_RESPONSE


def _retry_delay(exc: Exception, attempt: int, jitter: Callable[[], float]) -> float | None:
    """Retry only transient failures; never retry earlier than provider guidance.

    A delay beyond 30 seconds is surfaced to the user instead of sleeping less
    than requested. Ambiguous/daily/zero-quota 429s are not retried.
    """
    provider_delays = []
    if isinstance(exc, errors.APIError):
        if exc.code not in {408, 429, 500, 502, 503, 504}:
            return None
        body = exc.details if isinstance(exc.details, dict) else {}
        body = body.get("error", body)
        if not isinstance(body, dict):
            return None
        details = body.get("details", [])
        details = details if isinstance(details, list) else []
        quota = [d for d in details if isinstance(d, dict) and str(d.get("@type", "")).endswith("QuotaFailure")]
        if exc.code == 429:
            # Daily/spend/unknown quota failures require account review, not retry.
            if any(not isinstance(d.get("violations"), list) for d in quota):
                return None
            violations = [v for d in quota for v in d["violations"] if isinstance(v, dict)]
            if quota and (not violations or any("perminute" not in str(v.get("quotaId", "")).lower()
                                                or str(v.get("quotaValue", "")) == "0" for v in violations)):
                return None
            message = str(body.get("message", "")).lower()
            if any(word in message for word in ("daily", "perday", "billing", "limit: 0", "spend")):
                return None
            if "quota" in message and not violations:
                return None
        try:
            headers = getattr(getattr(exc, "response", None), "headers", {})
            retry_after = headers.get("retry-after")
            if retry_after is not None:
                try:
                    seconds = float(retry_after)
                except ValueError:
                    seconds = (parsedate_to_datetime(retry_after) - datetime.now(timezone.utc)).total_seconds()
                provider_delays.append(max(0.0, seconds) if math.isfinite(seconds) else math.inf)
            for detail in details:
                if isinstance(detail, dict) and str(detail.get("@type", "")).endswith("RetryInfo"):
                    seconds = float(str(detail["retryDelay"]).removesuffix("s"))
                    provider_delays.append(seconds if math.isfinite(seconds) and seconds >= 0 else math.inf)
        except (ValueError, TypeError, KeyError, OverflowError):
            return None  # Malformed provider directions are not permission to retry.
        if exc.code == 429 and not provider_delays:
            return None
    elif _error_code(exc) not in {LLMErrorCode.TIMEOUT, LLMErrorCode.UNAVAILABLE}:
        return None
    delay = max([min(0.5 * 2 ** attempt, 8) * (1 + jitter()), *provider_delays])
    return delay if delay <= 30 else None
