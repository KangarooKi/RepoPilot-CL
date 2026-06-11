from __future__ import annotations

import json
import os
import ssl
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

try:
    import certifi
except ImportError:  # pragma: no cover - optional runtime dependency
    certifi = None


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


class DeepSeekClient:
    """Minimal OpenAI-compatible DeepSeek chat client.

    The agent loop does not depend on this client yet; it is provided so the
    DeepSeek V4 integration has a clear future entry point.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "deepseek-v4-flash",
        base_url: str = "https://api.deepseek.com",
        reasoning_effort: str = "max",
        thinking_enabled: bool = True,
        ca_bundle: str | None = None,
        allow_insecure_ssl: bool = False,
        timeout_sec: int = 120,
    ) -> None:
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.reasoning_effort = reasoning_effort
        self.thinking_enabled = thinking_enabled
        self.ca_bundle = ca_bundle or os.environ.get("SSL_CERT_FILE")
        self.allow_insecure_ssl = allow_insecure_ssl or (
            os.environ.get("REPOPILOT_ALLOW_INSECURE_SSL") == "1"
        )
        self.timeout_sec = timeout_sec

    def chat(self, messages: list[ChatMessage], temperature: float = 1.0) -> str:
        payload = self.chat_payload(messages, temperature=temperature)
        return payload["choices"][0]["message"]["content"]

    def chat_payload(
        self,
        messages: list[ChatMessage],
        temperature: float = 1.0,
    ) -> dict[str, object]:
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is required for DeepSeekClient.chat().")

        body = {
            "model": self.model,
            "messages": [message.__dict__ for message in messages],
            "temperature": temperature,
            "thinking": {"type": "enabled" if self.thinking_enabled else "disabled"},
            "reasoning_effort": self.reasoning_effort,
            "stream": False,
        }
        request = urllib.request.Request(
            self.chat_completions_url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(
            request,
            timeout=self.timeout_sec,
            context=self.ssl_context,
        ) as response:
            return json.loads(response.read().decode("utf-8"))

    @property
    def chat_completions_url(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return urljoin(f"{self.base_url}/", "chat/completions")

    @property
    def ssl_context(self) -> ssl.SSLContext:
        if self.allow_insecure_ssl:
            return ssl._create_unverified_context()
        if self.ca_bundle:
            return ssl.create_default_context(cafile=str(Path(self.ca_bundle)))
        if certifi is not None:
            return ssl.create_default_context(cafile=certifi.where())
        return ssl.create_default_context()
