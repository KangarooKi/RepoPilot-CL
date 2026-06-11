from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from repopilot.agent.loop import AgentRunResult
from repopilot.benchmark.task_loader import Task, load_task


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
        files.extend(sorted(Path().glob(pattern)))
    unique = sorted({file.resolve() for file in files})
    return unique


def run_tasks(
    task_files: list[Path],
    run_one: Callable[[Task], AgentRunResult],
) -> BenchmarkSummary:
    task_summaries: list[TaskRunSummary] = []
    for task_file in task_files:
        task = load_task(task_file)
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

