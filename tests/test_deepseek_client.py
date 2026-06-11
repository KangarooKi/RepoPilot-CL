import json
import unittest
from unittest.mock import patch

from repopilot.models.deepseek_client import ChatMessage, DeepSeekClient


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return json.dumps(
            {"choices": [{"message": {"content": "hello"}}]}
        ).encode("utf-8")


class DeepSeekClientTest(unittest.TestCase):
    def test_payload_matches_deepseek_v4_chat_format(self) -> None:
        captured = {}

        def fake_urlopen(request, timeout, context):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["headers"] = dict(request.header_items())
            captured["timeout"] = timeout
            captured["context"] = context
            return _FakeResponse()

        client = DeepSeekClient(
            api_key="test-key",
            model="deepseek-v4-flash",
            base_url="https://api.deepseek.com",
            reasoning_effort="max",
            thinking_enabled=True,
        )

        with patch("urllib.request.urlopen", fake_urlopen):
            content = client.chat([ChatMessage(role="user", content="Hello!")])

        self.assertEqual(content, "hello")
        self.assertEqual(captured["url"], "https://api.deepseek.com/chat/completions")
        self.assertEqual(captured["body"]["model"], "deepseek-v4-flash")
        self.assertEqual(captured["body"]["temperature"], 1.0)
        self.assertEqual(captured["body"]["thinking"], {"type": "enabled"})
        self.assertEqual(captured["body"]["reasoning_effort"], "max")
        self.assertFalse(captured["body"]["stream"])
        self.assertEqual(captured["body"]["messages"][0]["content"], "Hello!")
        self.assertIsNotNone(captured["context"])


if __name__ == "__main__":
    unittest.main()
