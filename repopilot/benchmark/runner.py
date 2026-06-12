from __future__ import annotations

import glob
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from repopilot.agent.loop import AgentRunResult
from repopilot.benchmark.swebench import load_swebench_jsonl
from repopilot.benchmark.task_loader import Task, load_tasks


@dataclass(frozen=True)
class TaskRunSummary:
    task_id: str
    repo: str
    resolved: bool
    patch_lines: int
    workdir: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BenchmarkSummary:
    total: int
    resolved: int
    resolved_rate: float
    tasks: list[TaskRunSummary]

    def to_dict(self) -> dict[str, object]:
        return {
            "total": self.total,
            "resolved": self.resolved,
            "resolved_rate": self.resolved_rate,
            "tasks": [task.to_dict() for task in self.tasks],
        }


def discover_task_files(patterns: list[str]) -> list[Path]:
    files: list[Path] = []
    for pattern in patterns:
        path = Path(pattern)
        if path.is_file():
            files.append(path)
            continue
        files.extend(Path(match) for match in sorted(glob.glob(pattern)))
    unique = sorted({file.resolve() for file in files})
    return unique


def run_tasks(
    tasks: list[Task],
    run_one: Callable[[Task], AgentRunResult],
) -> BenchmarkSummary:
    task_summaries: list[TaskRunSummary] = []
    for task in tasks:
        result = run_one(task)
        task_summaries.append(
            TaskRunSummary(
                task_id=task.task_id,
                repo=task.repo,
                resolved=result.resolved,
                patch_lines=len(result.patch.splitlines()),
                workdir=str(result.workdir),
            )
        )

    resolved = sum(1 for task in task_summaries if task.resolved)
    total = len(task_summaries)
    return BenchmarkSummary(
        total=total,
        resolved=resolved,
        resolved_rate=resolved / total if total else 0.0,
        tasks=task_summaries,
    )


def load_task_inputs(
    task_files: list[Path],
    *,
    input_format: str = "repopilot",
    limit: int | None = None,
) -> list[Task]:
    tasks: list[Task] = []
    for task_file in task_files:
        if input_format == "swebench":
            remaining = _remaining(limit, tasks)
            if remaining == 0:
                return tasks
            tasks.extend(load_swebench_jsonl(task_file, limit=remaining))
        else:
            tasks.extend(load_tasks(task_file))
        if limit is not None and len(tasks) >= limit:
            return tasks[:limit]
    return tasks


def filter_tasks(
    tasks: list[Task],
    *,
    task_ids: set[str] | None = None,
    repo_contains: str | None = None,
    max_fail_to_pass: int | None = None,
    max_pass_to_pass: int | None = None,
) -> list[Task]:
    filtered = tasks
    if task_ids is not None:
        filtered = [task for task in filtered if task.task_id in task_ids]
    if repo_contains:
        filtered = [task for task in filtered if repo_contains in task.repo]
    if max_fail_to_pass is not None:
        filtered = [
            task
            for task in filtered
            if len(task.fail_to_pass_tests) <= max_fail_to_pass
        ]
    if max_pass_to_pass is not None:
        filtered = [
            task
            for task in filtered
            if len(task.pass_to_pass_tests) <= max_pass_to_pass
        ]
    return filtered


def _remaining(limit: int | None, tasks: list[Task]) -> int | None:
    if limit is None:
        return None
    return max(0, limit - len(tasks))
