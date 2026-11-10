"""Explicit, side-effect-free configuration with safe diagnostics.

Precedence: process environment > Streamlit secrets > optional dotenv > defaults.
An explicitly blank value overrides lower-priority values (including a key).
No configuration is loaded on import; no SDK clients are created here.
"""

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values


class ConfigurationError(ValueError):
    """Messages contain setting names/instructions, never supplied values."""


@dataclass(frozen=True)
class Settings:
    app_mode: str = "production"
    llm_provider: str = "gemini"
    gemini_model: str | None = None
    gemini_api_key: str | None = field(default=None, repr=False)
    groq_api_key: str | None = field(default=None, repr=False)
    groq_model: str = "whisper-large-v3-turbo"
    speech_timeout_seconds: int = 30
    llm_timeout_seconds: int = 30
    llm_max_retries: int = 1
    llm_max_output_tokens: int = 2048

    def __post_init__(self) -> None:
        if self.app_mode not in {"production", "development"}:
            raise ConfigurationError("APP_MODE must be production or development.")
        if not isinstance(self.groq_model, str) or not self.groq_model.strip():
            raise ConfigurationError("GROQ_MODEL must be non-empty text.")
        if not isinstance(self.llm_provider, str) or not self.llm_provider.strip():
            raise ConfigurationError("LLM_PROVIDER must be non-empty text.")
        for name in ("gemini_model", "gemini_api_key", "groq_api_key"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ConfigurationError(f"{name.upper()} must be non-empty text or unset.")
        for name, lower, upper in (
            ("speech_timeout_seconds", 1, 60),
            ("llm_timeout_seconds", 1, 90),
            ("llm_max_retries", 0, 1),
            ("llm_max_output_tokens", 1, 8192),
        ):
            value = getattr(self, name)
            if type(value) is not int or not lower <= value <= upper:
                raise ConfigurationError(f"{name.upper()} must be an integer from {lower} to {upper}.")

    def require_gemini(self) -> None:
        missing = [name for name in ("GEMINI_API_KEY", "GEMINI_MODEL")
                   if getattr(self, name.lower()) is None]
        if missing:
            raise ConfigurationError("Configure " + ", ".join(missing) + " in private settings.")

    def require_groq(self) -> None:
        if self.groq_api_key is None:
            raise ConfigurationError("Configure GROQ_API_KEY in private settings to enable voice.")


def load_settings(
    *,
    environ: Mapping[str, str] | None = None,
    secrets: Mapping[str, object] | None = None,
    dotenv_path: str | Path | None = None,
) -> Settings:
    """Load only known keys, without mutating environment or discovering files."""
    values: dict[str, object] = {}
    if dotenv_path is not None:
        try:
            # No interpolation: prevent accidental substitution of unrelated secrets.
            values.update(dotenv_values(dotenv_path, interpolate=False, encoding="utf-8"))
        except (OSError, UnicodeError):
            raise ConfigurationError("Could not read the local environment file.") from None
    if secrets is not None:
        values.update(secrets)
    values.update(dict(os.environ) if environ is None else environ)

    def text(name: str, default: str | None = None) -> str | None:
        value = values.get(name, default)
        if value is None:
            return None
        if not isinstance(value, str):
            raise ConfigurationError(f"{name} must be text.")
        return value.strip() or None

    def integer(name: str, default: int) -> int:
        value = values.get(name, default)
        if type(value) is int:
            return value
        if not isinstance(value, str):
            raise ConfigurationError(f"{name} must be an integer.")
        try:
            return int(value)
        except ValueError:
            raise ConfigurationError(f"{name} must be an integer.") from None

    provider = text("LLM_PROVIDER", "gemini")
    if provider is None:
        raise ConfigurationError("LLM_PROVIDER must be non-empty text.")
    return Settings(
        app_mode=text("APP_MODE", "production"),
        llm_provider=provider,
        gemini_model=text("GEMINI_MODEL"),
        gemini_api_key=text("GEMINI_API_KEY"),
        groq_api_key=text("GROQ_API_KEY"),
        groq_model=text("GROQ_MODEL", "whisper-large-v3-turbo"),
        speech_timeout_seconds=integer("SPEECH_TIMEOUT_SECONDS", 30),
        llm_timeout_seconds=integer("LLM_TIMEOUT_SECONDS", 30),
        llm_max_retries=integer("LLM_MAX_RETRIES", 1),
        llm_max_output_tokens=integer("LLM_MAX_OUTPUT_TOKENS", 2048),
    )


def load_streamlit_settings(
    *, dotenv_path: str | Path | None = None,
    secrets_loader: Callable[[], Mapping[str, object]] | None = None,
) -> Settings:
    """UI boundary: optional Streamlit secrets, with injectable loader for tests.

    Snapshot environment before Streamlit reads root secrets, since Streamlit
    may copy those values into os.environ. This preserves environment precedence.
    """
    from streamlit.errors import StreamlitSecretNotFoundError

    environment = dict(os.environ)
    if secrets_loader is None:
        def secrets_loader() -> Mapping[str, object]:
            import streamlit as st
            return st.secrets.to_dict()
    try:
        secrets = secrets_loader()
    except StreamlitSecretNotFoundError as error:
        # Streamlit also uses this exception for malformed TOML and bad paths.
        if error.error_id != "no-secrets-found":
            raise ConfigurationError("Could not load Streamlit secrets; check private settings.") from None
        secrets = {}
    except FileNotFoundError:
        secrets = {}
    except Exception:
        # SDK/parse errors can contain secrets or file contents. Never expose them.
        raise ConfigurationError("Could not load Streamlit secrets; check private settings.") from None
    return load_settings(environ=environment, secrets=secrets, dotenv_path=dotenv_path)
