"""Explicit adapter registration; never silently use a fake in production."""

from collections.abc import Callable, Mapping

from nyayasaathi.config import ConfigurationError, Settings
from nyayasaathi.llm.base import LLMClient, LLMError, LLMErrorCode


def create_llm_client(
    settings: Settings,
    *, builders: Mapping[str, Callable[[Settings], LLMClient]] | None = None,
    allow_live: bool = False,
) -> LLMClient:
    if builders is None:
        from nyayasaathi.llm.gemini import GeminiLLM
        from nyayasaathi.llm.simulated import SimulatedLLM
        registry = {"simulation": lambda _: SimulatedLLM()}
        if allow_live:
            registry["gemini"] = lambda config: GeminiLLM(config, allow_live=True)
    else:
        registry = builders
    builder = registry.get(settings.llm_provider)
    if builder is None:
        raise LLMError(LLMErrorCode.UNAVAILABLE)
    client = builder(settings)
    if not isinstance(client, LLMClient) or not callable(client.generate):
        raise ConfigurationError("The configured adapter must implement generate().")
    return client
