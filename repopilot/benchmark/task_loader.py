from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Task:
    """A repository-level repair task.

    The MVP supports inline `initial_files` so toy tasks can run without
    downloading a benchmark repository. SWE-bench loaders can later populate the
    same schema from official instances.
    """

    task_id: str
    repo: str
    issue: str
    test_command: str
    base_commit: str | None = None
    fail_to_pass_tests: list[str] = field(default_factory=list)
    pass_to_pass_tests: list[str] = field(default_factory=list)
    initial_files: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Task":
        required = ["task_id", "repo", "issue", "test_command"]
        missing = [key for key in required if key not in payload]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"Task is missing required field(s): {joined}")

        return cls(
            task_id=str(payload["task_id"]),
            repo=str(payload["repo"]),
            issue=str(payload["issue"]),
            test_command=str(payload["test_command"]),
            base_commit=payload.get("base_commit"),
            fail_to_pass_tests=list(payload.get("fail_to_pass_tests", [])),
            pass_to_pass_tests=list(payload.get("pass_to_pass_tests", [])),
            initial_files=dict(payload.get("initial_files", {})),
            metadata=dict(payload.get("metadata", {})),
        )


def load_task(path: str | Path) -> Task:
    task_path = Path(path)
    with task_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return Task.from_dict(payload)

