from __future__ import annotations

from collections import Counter
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TaskReport:
    task_id: str
    repo: str
    resolved: bool
    patch_lines: int
    model_steps: int
    tool_steps: int
    test_runs: int
    changed_files: list[str]
    failure_type: str
    model_errors: int
    invalid_actions: int
    issue_title: str
    patch_preview: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BenchmarkReport:
    total: int
    resolved: int
    resolved_rate: float
    avg_patch_lines: float
    avg_model_steps: float
    avg_tool_steps: float
    avg_test_runs: float
    model_error_tasks: int
    timeout_tasks: int
    failure_types: dict[str, int]
    tasks: list[TaskReport]

    def to_dict(self) -> dict[str, object]:
        return {
            "total": self.total,
            "resolved": self.resolved,
            "resolved_rate": self.resolved_rate,
            "avg_patch_lines": self.avg_patch_lines,
            "avg_model_steps": self.avg_model_steps,
            "avg_tool_steps": self.avg_tool_steps,
            "avg_test_runs": self.avg_test_runs,
            "model_error_tasks": self.model_error_tasks,
            "timeout_tasks": self.timeout_tasks,
            "failure_types": self.failure_types,
            "tasks": [task.to_dict() for task in self.tasks],
        }


def load_benchmark_report(
    summary_path: str | Path,
    trajectory_path: str | Path,
) -> BenchmarkReport:
    summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    trajectories = _load_trajectories(trajectory_path)
    tasks = [
        _build_task_report(task_summary, trajectories.get(str(task_summary["task_id"])))
        for task_summary in summary.get("tasks", [])
    ]
    return build_benchmark_report(tasks)


def build_benchmark_report(tasks: list[TaskReport]) -> BenchmarkReport:
    total = len(tasks)
    resolved = sum(1 for task in tasks if task.resolved)
    return BenchmarkReport(
        total=total,
        resolved=resolved,
        resolved_rate=resolved / total if total else 0.0,
        avg_patch_lines=_average(task.patch_lines for task in tasks),
        avg_model_steps=_average(task.model_steps for task in tasks),
        avg_tool_steps=_average(task.tool_steps for task in tasks),
        avg_test_runs=_average(task.test_runs for task in tasks),
        model_error_tasks=sum(1 for task in tasks if task.model_errors > 0),
        timeout_tasks=sum(1 for task in tasks if task.failure_type == "model_timeout"),
        failure_types=dict(sorted(Counter(task.failure_type for task in tasks).items())),
        tasks=tasks,
    )


def render_markdown_report(report: BenchmarkReport, title: str = "RepoPilot-CL Benchmark Report") -> str:
    lines = [
        f"# {title}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Tasks | {report.total} |",
        f"| Resolved | {report.resolved} |",
        f"| Resolved Rate | {report.resolved_rate:.3f} |",
        f"| Avg Patch Lines | {report.avg_patch_lines:.1f} |",
        f"| Avg Model Steps | {report.avg_model_steps:.1f} |",
        f"| Avg Tool Steps | {report.avg_tool_steps:.1f} |",
        f"| Avg Test Runs | {report.avg_test_runs:.1f} |",
        f"| Model Error Tasks | {report.model_error_tasks} |",
        f"| Timeout Tasks | {report.timeout_tasks} |",
        "",
        "## Failure Types",
        "",
        "| Failure Type | Tasks |",
        "|---|---:|",
    ]
    for failure_type, count in report.failure_types.items():
        lines.append(f"| `{failure_type}` | {count} |")

    lines.extend([
        "",
        "## Tasks",
        "",
        "| Task | Resolved | Patch Lines | Model Steps | Tool Steps | Test Runs | Failure Type | Changed Files |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ])
    for task in report.tasks:
        lines.append(
            (
                f"| `{task.task_id}` | {_yes_no(task.resolved)} | {task.patch_lines} | "
                f"{task.model_steps} | {task.tool_steps} | {task.test_runs} | "
                f"{task.failure_type} | {_format_files(task.changed_files)} |"
            )
        )

    lines.extend(["", "## Case Studies", ""])
    for task in report.tasks:
        lines.extend(
            [
                f"### `{task.task_id}`",
                "",
                f"- Repository: `{task.repo}`",
                f"- Issue: {task.issue_title or 'n/a'}",
                f"- Outcome: {_yes_no(task.resolved)}; failure type: `{task.failure_type}`",
                f"- Steps: model={task.model_steps}, tools={task.tool_steps}, tests={task.test_runs}",
                f"- Changed files: {_format_files(task.changed_files)}",
            ]
        )
        if task.patch_preview:
            lines.extend(["", "```diff", task.patch_preview.rstrip(), "```"])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_report_artifacts(
    report: BenchmarkReport,
    markdown_path: str | Path,
    json_path: str | Path | None = None,
    *,
    title: str = "RepoPilot-CL Benchmark Report",
) -> None:
    md_path = Path(markdown_path)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown_report(report, title=title), encoding="utf-8")
    if json_path is not None:
        path = Path(json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")


def _build_task_report(
    task_summary: dict[str, Any],
    trajectory: dict[str, Any] | None,
) -> TaskReport:
    trajectory = trajectory or {}
    steps = list(trajectory.get("steps", []))
    final_patch = str(trajectory.get("final_patch") or "")
    resolved = bool(task_summary.get("resolved", trajectory.get("resolved", False)))
    model_errors = sum(1 for step in steps if step.get("action") == "model_call_error")
    invalid_actions = sum(1 for step in steps if step.get("action") == "model_action_invalid")
    return TaskReport(
        task_id=str(task_summary.get("task_id", trajectory.get("task_id", ""))),
        repo=str(task_summary.get("repo", trajectory.get("repo", ""))),
        resolved=resolved,
        patch_lines=int(task_summary.get("patch_lines") or _line_count(final_patch)),
        model_steps=sum(1 for step in steps if step.get("action") == "model_action"),
        tool_steps=sum(1 for step in steps if str(step.get("action", "")).startswith("tool:")),
        test_runs=_max_test_runs(steps),
        changed_files=_changed_files(final_patch),
        failure_type=_failure_type(resolved, final_patch, steps),
        model_errors=model_errors,
        invalid_actions=invalid_actions,
        issue_title=_issue_title(str(trajectory.get("issue", ""))),
        patch_preview=_patch_preview(final_patch),
    )


def _load_trajectories(path: str | Path) -> dict[str, dict[str, Any]]:
    trajectories: dict[str, dict[str, Any]] = {}
    trajectory_path = Path(path)
    if not trajectory_path.exists():
        return trajectories
    with trajectory_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            trajectories[str(payload.get("task_id", ""))] = payload
    return trajectories


def _failure_type(resolved: bool, patch: str, steps: list[dict[str, Any]]) -> str:
    if resolved:
        return "resolved"
    for step in steps:
        if step.get("action") == "prepare_error":
            observation = str(step.get("observation", ""))
            if "Setup command failed" in observation:
                return "setup_error"
            if "Repo install failed" in observation:
                return "repo_install_error"
            if "Failed to apply task test_patch" in observation:
                return "test_patch_error"
            return "prepare_error"
    for step in steps:
        if step.get("action") == "model_call_error":
            observation = str(step.get("observation", ""))
            if "TimeoutError" in observation:
                return "model_timeout"
            return "model_call_error"
    if any(step.get("action") == "propose_patch_error" for step in steps):
        return "patch_provider_error"
    if not patch.strip():
        return "no_patch"
    return "unresolved_patch"


def _max_test_runs(steps: list[dict[str, Any]]) -> int:
    values = [
        int(metadata["test_runs"])
        for step in steps
        if isinstance((metadata := step.get("metadata", {})), dict)
        and isinstance(metadata.get("test_runs"), int)
    ]
    if values:
        return max(values)
    return sum(
        1
        for step in steps
        if step.get("action") in {"verify_baseline", "tool:run_tests", "tool:submit"}
    )


def _changed_files(patch: str) -> list[str]:
    files: list[str] = []
    for line in patch.splitlines():
        if not line.startswith("diff --git "):
            continue
        parts = line.split()
        if len(parts) >= 4:
            files.append(_strip_prefix(parts[3]))
    return sorted(set(files))


def _patch_preview(patch: str, max_lines: int = 24) -> str:
    lines = patch.splitlines()
    if len(lines) <= max_lines:
        return patch
    return "\n".join(lines[:max_lines] + ["..."])


def _format_files(files: list[str]) -> str:
    return ", ".join(f"`{file}`" for file in files) if files else "none"


def _strip_prefix(path: str) -> str:
    if path.startswith("a/") or path.startswith("b/"):
        return path[2:]
    return path


def _issue_title(issue: str) -> str:
    for line in issue.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _line_count(text: str) -> int:
    return len(text.splitlines())


def _average(values) -> float:
    items = list(values)
    return sum(items) / len(items) if items else 0.0


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"
