"""Provider-neutral transport contracts; legal extraction schemas come later.

These contracts validate transport shape, not legal truth. Response text must
never be displayed as verified legal guidance without later safety validation.
"""

from dataclasses import dataclass, field
from typing import Literal


def require_text(value: object, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text.")


def require_int(value: object, label: str, minimum: int, maximum: int) -> None:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{label} must be an integer from {minimum} to {maximum}.")


@dataclass(frozen=True)
class Message:
    role: Literal["user", "assistant"]
    content: str = field(repr=False)

    def __post_init__(self) -> None:
        if self.role not in ("user", "assistant"):
            raise ValueError("Message role must be user or assistant.")
        require_text(self.content, "Message content")


@dataclass(frozen=True)
class LLMRequest:
    system_instruction: str = field(repr=False)
    messages: tuple[Message, ...] = field(repr=False)
    max_output_tokens: int = 2048
    response_format: Literal["json", "text"] = "json"

    def __post_init__(self) -> None:
        require_text(self.system_instruction, "System instruction")
        if not isinstance(self.messages, tuple) or not self.messages:
            raise ValueError("Messages must be a non-empty tuple.")
        if any(not isinstance(message, Message) for message in self.messages):
            raise ValueError("Messages must contain Message objects only.")
        require_int(self.max_output_tokens, "Output token limit", 1, 8192)
        if self.response_format not in ("json", "text"):
            raise ValueError("Response format must be json or text.")


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None

    def __post_init__(self) -> None:
        for value in (self.input_tokens, self.output_tokens):
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("Token counts must be non-negative integers or unknown.")


@dataclass(frozen=True)
class LLMResponse:
    text: str = field(repr=False)
    model: str
    usage: TokenUsage = field(default_factory=TokenUsage)

    def __post_init__(self) -> None:
        require_text(self.text, "Response text")
        require_text(self.model, "Model identifier")
        if not isinstance(self.usage, TokenUsage):
            raise ValueError("Usage must be a TokenUsage object.")
