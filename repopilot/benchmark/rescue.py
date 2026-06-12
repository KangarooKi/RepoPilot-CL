from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class RescueCase:
    task_id: str
    repo: str
    failure_type: str
    issue_title: str
    changed_files: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def load_rescue_cases(
    report_path: str | Path,
    *,
    failure_types: set[str] | None = None,
) -> list[RescueCase]:
    payload = json.loads(Path(report_path).read_text(encoding="utf-8"))
    cases: list[RescueCase] = []
    for task in payload.get("tasks", []):
        if bool(task.get("resolved")):
            continue
        failure_type = str(task.get("failure_type") or _fallback_failure_type(task))
        if failure_types is not None and failure_type not in failure_types:
            continue
        cases.append(
            RescueCase(
                task_id=str(task.get("task_id", "")),
                repo=str(task.get("repo", "")),
                failure_type=failure_type,
                issue_title=str(task.get("issue_title", "")),
                changed_files=[str(file) for file in task.get("changed_files", [])],
            )
        )
    return [case for case in cases if case.task_id]


def write_rescue_task_ids(cases: list[RescueCase], path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(case.task_id for case in cases) + "\n", encoding="utf-8")


def render_rescue_markdown(
    cases: list[RescueCase],
    *,
    source_report: str | Path,
    task_ids_path: str | Path,
    recommended_command: str | None = None,
) -> str:
    counts = Counter(case.failure_type for case in cases)
    lines = [
        "# Rescue Plan",
        "",
        f"- Source report: `{source_report}`",
        f"- Task id file: `{task_ids_path}`",
        f"- Unresolved tasks: `{len(cases)}`",
        "",
        "## Failure Mix",
        "",
        "| Failure Type | Count |",
        "|---|---:|",
    ]
    for failure_type, count in sorted(counts.items()):
        lines.append(f"| `{failure_type}` | {count} |")

    lines.extend(
        [
            "",
            "## Cases",
            "",
            "| Task | Repository | Failure Type | Changed Files | Issue |",
            "|---|---|---|---|---|",
        ]
    )
    for case in cases:
        lines.append(
            (
                f"| `{case.task_id}` | `{case.repo}` | `{case.failure_type}` | "
                f"{_format_files(case.changed_files)} | {_escape_table_cell(case.issue_title)} |"
            )
        )

    if recommended_command:
        lines.extend(
            [
                "",
                "## Recommended Rerun",
                "",
                "```bash",
                recommended_command,
                "```",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_rescue_markdown(
    cases: list[RescueCase],
    path: str | Path,
    *,
    source_report: str | Path,
    task_ids_path: str | Path,
    recommended_command: str | None = None,
) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render_rescue_markdown(
            cases,
            source_report=source_report,
            task_ids_path=task_ids_path,
            recommended_command=recommended_command,
        ),
        encoding="utf-8",
    )


def _fallback_failure_type(task: dict[str, object]) -> str:
    patch_lines = int(task.get("patch_lines") or 0)
    return "no_patch" if patch_lines == 0 else "unresolved_patch"


def _format_files(files: list[str]) -> str:
    return ", ".join(f"`{file}`" for file in files) if files else "none"


def _escape_table_cell(text: str) -> str:
    return text.replace("|", "\\|")
