"""Make accidental outbound calls fail and isolate tests from local secrets."""

import socket

import pytest


@pytest.fixture(autouse=True)
def offline_environment(monkeypatch, tmp_path):
    for name in (
        "GEMINI_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY", "GEMINI_MODEL",
        "LLM_PROVIDER", "LLM_TIMEOUT_SECONDS", "LLM_MAX_RETRIES",
        "LLM_MAX_OUTPUT_TOKENS",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)

    def blocked(*args, **kwargs):
        raise AssertionError("Network access is forbidden in offline tests.")

    original_connect = socket.socket.connect

    def local_connect(sock, address):
        # Windows asyncio uses a loopback socket pair for its internal wakeup.
        # Permit literal loopback only, never DNS or external provider hosts.
        if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1"):
            return original_connect(sock, address)
        return blocked()

    monkeypatch.setattr(socket.socket, "connect", local_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
