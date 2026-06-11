from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


ALLOWED_ACTIONS = {
    "search_code",
    "read_file",
    "replace_text",
    "apply_patch",
    "run_tests",
    "get_diff",
    "submit",
}


@dataclass(frozen=True)
class AgentAction:
    name: str
    args: dict[str, Any] = field(default_factory=dict)
    thought: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"action": self.name, "args": self.args, "thought": self.thought}


def parse_action(text: str) -> AgentAction:
    payload = extract_json_object(text)
    if payload is None:
        raise ValueError("Model response did not contain a JSON object.")

    action_name = payload.get("action")
    if not isinstance(action_name, str):
        raise ValueError("Action JSON must contain a string `action` field.")
    if action_name not in ALLOWED_ACTIONS:
        allowed = ", ".join(sorted(ALLOWED_ACTIONS))
        raise ValueError(f"Unsupported action `{action_name}`. Allowed actions: {allowed}.")

    args = payload.get("args", {})
    if args is None:
        args = {}
    if not isinstance(args, dict):
        raise ValueError("Action `args` must be an object.")

    thought = payload.get("thought", "")
    return AgentAction(name=action_name, args=args, thought=str(thought))


def extract_json_object(text: str) -> dict[str, Any] | None:
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.S)
    candidate = fence_match.group(1).strip() if fence_match else text.strip()

    try:
        payload = json.loads(candidate)
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        pass

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        payload = json.loads(candidate[start : end + 1])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None
