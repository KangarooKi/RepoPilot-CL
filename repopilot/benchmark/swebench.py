from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from repopilot.benchmark.task_loader import Task


def swebench_record_to_task(
    record: dict[str, Any],
    *,
    test_command: str | None = None,
    repo_url_template: str = "https://github.com/{repo}.git",
) -> Task:
    """Convert a SWE-bench-style record into RepoPilot's generic Task schema.

    The official records include fields such as `instance_id`, `repo`,
    `base_commit`, `problem_statement`, `FAIL_TO_PASS`, and `PASS_TO_PASS`.
    RepoPilot keeps the loader permissive so locally exported subsets and
    SWE-Bench-CL streams can use the same adapter.
    """

    repo = str(record["repo"])
    instance_id = str(record.get("instance_id") or record.get("task_id"))
    if not instance_id:
        raise ValueError("SWE-bench record is missing `instance_id`.")

    issue = str(record.get("problem_statement") or record.get("issue") or "")
    hints = str(record.get("hints_text") or "").strip()
    if hints:
        issue = f"{issue}\n\nHints:\n{hints}"

    fail_to_pass = _coerce_list(record.get("FAIL_TO_PASS") or record.get("fail_to_pass_tests"))
    pass_to_pass = _coerce_list(record.get("PASS_TO_PASS") or record.get("pass_to_pass_tests"))
    command = test_command or str(
        record.get("test_command")
        or record.get("eval_command")
        or _default_pytest_command(fail_to_pass, pass_to_pass)
    )

    metadata = {
        "source": "swebench",
        "version": record.get("version"),
        "environment_setup_commit": record.get("environment_setup_commit"),
        "test_patch": record.get("test_patch", ""),
        "gold_patch": record.get("patch", ""),
        "raw": record,
    }

    return Task(
        task_id=instance_id,
        repo=repo,
        repo_url=str(record.get("repo_url") or repo_url_template.format(repo=repo)),
        local_repo_path=record.get("local_repo_path"),
        base_commit=record.get("base_commit"),
        issue=issue,
        test_command=command,
        setup_command=record.get("setup_command"),
        fail_to_pass_tests=fail_to_pass,
        pass_to_pass_tests=pass_to_pass,
        metadata=metadata,
    )


def load_swebench_jsonl(
    path: str | Path,
    *,
    test_command: str | None = None,
    limit: int | None = None,
) -> list[Task]:
    if limit == 0:
        return []

    tasks: list[Task] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            tasks.append(
                swebench_record_to_task(json.loads(line), test_command=test_command)
            )
            if limit is not None and len(tasks) >= limit:
                break
    return tasks


def _coerce_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
        return [value]
    return [str(value)]


def _default_pytest_command(
    fail_to_pass: list[str],
    pass_to_pass: list[str],
) -> str:
    tests = fail_to_pass or pass_to_pass
    if not tests:
        return "python3 -m pytest"
    return "python3 -m pytest " + " ".join(tests)
