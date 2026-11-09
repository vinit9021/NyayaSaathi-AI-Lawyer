"""Explicit adapter registration; never silently use a fake in production."""

from collections.abc import Callable, Mapping

from nyayasaathi.config import ConfigurationError, Settings
from nyayasaathi.llm.base import LLMClient, LLMError, LLMErrorCode


def create_llm_client(
    settings: Settings,
    *, builders: Mapping[str, Callable[[Settings], LLMClient]] | None = None,
) -> LLMClient:
    # Gemini registration will be added with its real adapter in milestone 3.
    registry = {} if builders is None else builders
    builder = registry.get(settings.llm_provider)
    if builder is None:
        raise LLMError(LLMErrorCode.UNAVAILABLE)
    client = builder(settings)
    if not isinstance(client, LLMClient) or not callable(client.generate):
        raise ConfigurationError("The configured adapter must implement generate().")
    return client
