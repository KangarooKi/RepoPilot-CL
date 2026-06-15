from __future__ import annotations

from collections import Counter
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from repopilot.report.benchmark_report import BenchmarkReport, TaskReport


@dataclass(frozen=True)
class TaskComparison:
    task_id: str
    repo: str
    status: str
    base_resolved: bool | None
    candidate_resolved: bool | None
    base_failure_type: str
    candidate_failure_type: str
    issue_title: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BenchmarkComparison:
    base_name: str
    candidate_name: str
    base_total: int
    candidate_total: int
    common_tasks: int
    base_resolved: int
    candidate_resolved: int
    delta_resolved: int
    gained_tasks: int
    lost_tasks: int
    still_resolved: int
    still_unresolved: int
    base_only_tasks: int
    candidate_only_tasks: int
    failure_transitions: dict[str, int]
    tasks: list[TaskComparison]

    def to_dict(self) -> dict[str, object]:
        return {
            "base_name": self.base_name,
            "candidate_name": self.candidate_name,
            "base_total": self.base_total,
            "candidate_total": self.candidate_total,
            "common_tasks": self.common_tasks,
            "base_resolved": self.base_resolved,
            "candidate_resolved": self.candidate_resolved,
            "delta_resolved": self.delta_resolved,
            "gained_tasks": self.gained_tasks,
            "lost_tasks": self.lost_tasks,
            "still_resolved": self.still_resolved,
            "still_unresolved": self.still_unresolved,
            "base_only_tasks": self.base_only_tasks,
            "candidate_only_tasks": self.candidate_only_tasks,
            "failure_transitions": self.failure_transitions,
            "tasks": [task.to_dict() for task in self.tasks],
        }


def compare_benchmark_reports(
    base: BenchmarkReport,
    candidate: BenchmarkReport,
    *,
    base_name: str = "base",
    candidate_name: str = "candidate",
    task_order: list[str] | None = None,
) -> BenchmarkComparison:
    base_tasks = {task.task_id: task for task in base.tasks}
    candidate_tasks = {task.task_id: task for task in candidate.tasks}
    all_task_ids = _ordered_task_ids(base_tasks, candidate_tasks, task_order)
    tasks = [
        _compare_task(task_id, base_tasks.get(task_id), candidate_tasks.get(task_id))
        for task_id in all_task_ids
    ]
    transitions = Counter(
        f"{task.base_failure_type} -> {task.candidate_failure_type}"
        for task in tasks
        if task.status not in {"base_only", "candidate_only"}
    )
    return BenchmarkComparison(
        base_name=base_name,
        candidate_name=candidate_name,
        base_total=base.total,
        candidate_total=candidate.total,
        common_tasks=len(set(base_tasks) & set(candidate_tasks)),
        base_resolved=base.resolved,
        candidate_resolved=candidate.resolved,
        delta_resolved=candidate.resolved - base.resolved,
        gained_tasks=sum(1 for task in tasks if task.status == "gained"),
        lost_tasks=sum(1 for task in tasks if task.status == "lost"),
        still_resolved=sum(1 for task in tasks if task.status == "still_resolved"),
        still_unresolved=sum(1 for task in tasks if task.status == "still_unresolved"),
        base_only_tasks=sum(1 for task in tasks if task.status == "base_only"),
        candidate_only_tasks=sum(1 for task in tasks if task.status == "candidate_only"),
        failure_transitions=dict(sorted(transitions.items())),
        tasks=tasks,
    )


def render_comparison_markdown(
    comparison: BenchmarkComparison,
    *,
    title: str = "RepoPilot-CL Benchmark Comparison",
) -> str:
    delta = f"{comparison.delta_resolved:+d}"
    lines = [
        f"# {title}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Base report | `{comparison.base_name}` |",
        f"| Candidate report | `{comparison.candidate_name}` |",
        f"| Base tasks | {comparison.base_total} |",
        f"| Candidate tasks | {comparison.candidate_total} |",
        f"| Common tasks | {comparison.common_tasks} |",
        f"| Base resolved | {comparison.base_resolved} |",
        f"| Candidate resolved | {comparison.candidate_resolved} |",
        f"| Delta resolved | {delta} |",
        f"| Gained tasks | {comparison.gained_tasks} |",
        f"| Lost tasks | {comparison.lost_tasks} |",
        f"| Still resolved | {comparison.still_resolved} |",
        f"| Still unresolved | {comparison.still_unresolved} |",
        f"| Base-only tasks | {comparison.base_only_tasks} |",
        f"| Candidate-only tasks | {comparison.candidate_only_tasks} |",
        "",
        "## Failure Transitions",
        "",
        "| Transition | Tasks |",
        "|---|---:|",
    ]
    for transition, count in comparison.failure_transitions.items():
        lines.append(f"| `{transition}` | {count} |")

    lines.extend(
        [
            "",
            "## Task Outcomes",
            "",
            "| Task | Status | Base | Candidate | Repository | Issue |",
            "|---|---|---|---|---|---|",
        ]
    )
    for task in comparison.tasks:
        lines.append(
            (
                f"| `{task.task_id}` | `{task.status}` | "
                f"{_format_outcome(task.base_resolved, task.base_failure_type)} | "
                f"{_format_outcome(task.candidate_resolved, task.candidate_failure_type)} | "
                f"`{task.repo}` | {_escape_table_text(task.issue_title)} |"
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def write_comparison_artifacts(
    comparison: BenchmarkComparison,
    markdown_path: str | Path,
    json_path: str | Path | None = None,
    *,
    title: str = "RepoPilot-CL Benchmark Comparison",
) -> None:
    md_path = Path(markdown_path)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_comparison_markdown(comparison, title=title), encoding="utf-8")
    if json_path is not None:
        path = Path(json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(comparison.to_dict(), indent=2), encoding="utf-8")


def _ordered_task_ids(
    base_tasks: dict[str, TaskReport],
    candidate_tasks: dict[str, TaskReport],
    task_order: list[str] | None,
) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for task_id in task_order or []:
        if task_id in base_tasks or task_id in candidate_tasks:
            ordered.append(task_id)
            seen.add(task_id)
    for task_id in list(base_tasks) + list(candidate_tasks):
        if task_id not in seen:
            ordered.append(task_id)
            seen.add(task_id)
    return ordered


def _compare_task(
    task_id: str,
    base: TaskReport | None,
    candidate: TaskReport | None,
) -> TaskComparison:
    if base is None and candidate is None:
        raise ValueError(f"Cannot compare missing task `{task_id}`.")
    if base is None:
        assert candidate is not None
        return TaskComparison(
            task_id=task_id,
            repo=candidate.repo,
            status="candidate_only",
            base_resolved=None,
            candidate_resolved=candidate.resolved,
            base_failure_type="missing",
            candidate_failure_type=candidate.failure_type,
            issue_title=candidate.issue_title,
        )
    if candidate is None:
        return TaskComparison(
            task_id=task_id,
            repo=base.repo,
            status="base_only",
            base_resolved=base.resolved,
            candidate_resolved=None,
            base_failure_type=base.failure_type,
            candidate_failure_type="missing",
            issue_title=base.issue_title,
        )
    return TaskComparison(
        task_id=task_id,
        repo=candidate.repo or base.repo,
        status=_comparison_status(base.resolved, candidate.resolved),
        base_resolved=base.resolved,
        candidate_resolved=candidate.resolved,
        base_failure_type=base.failure_type,
        candidate_failure_type=candidate.failure_type,
        issue_title=candidate.issue_title or base.issue_title,
    )


def _comparison_status(base_resolved: bool, candidate_resolved: bool) -> str:
    if not base_resolved and candidate_resolved:
        return "gained"
    if base_resolved and not candidate_resolved:
        return "lost"
    if base_resolved and candidate_resolved:
        return "still_resolved"
    return "still_unresolved"


def _format_outcome(resolved: bool | None, failure_type: str) -> str:
    if resolved is None:
        return "`missing`"
    prefix = "yes" if resolved else "no"
    return f"{prefix} / `{failure_type}`"


def _escape_table_text(text: str) -> str:
    return text.replace("|", "\\|") if text else "n/a"
