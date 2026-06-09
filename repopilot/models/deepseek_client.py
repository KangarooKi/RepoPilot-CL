from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass


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
        base_url: str = "https://api.deepseek.com/chat/completions",
        timeout_sec: int = 120,
    ) -> None:
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.model = model
        self.base_url = base_url
        self.timeout_sec = timeout_sec

    def chat(self, messages: list[ChatMessage], temperature: float = 0.2) -> str:
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is required for DeepSeekClient.chat().")

        body = {
            "model": self.model,
            "messages": [message.__dict__ for message in messages],
            "temperature": temperature,
        }
        request = urllib.request.Request(
            self.base_url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload["choices"][0]["message"]["content"]

