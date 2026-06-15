from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from repopilot.report.benchmark_report import load_report_json


@dataclass(frozen=True)
class ValidationCheck:
    target_type: str
    path: str
    check: str
    passed: bool
    message: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ArtifactValidationReport:
    total_checks: int
    passed_checks: int
    failed_checks: int
    checks: list[ValidationCheck]

    @property
    def passed(self) -> bool:
        return self.failed_checks == 0

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "checks": [check.to_dict() for check in self.checks],
        }


def validate_artifacts(
    *,
    reports: list[str] | None = None,
    comparisons: list[str] | None = None,
    suites: list[str] | None = None,
    manifests: list[str] | None = None,
) -> ArtifactValidationReport:
    checks: list[ValidationCheck] = []
    for path in reports or []:
        checks.extend(validate_benchmark_report(path))
    for path in comparisons or []:
        checks.extend(validate_comparison_report(path))
    for path in suites or []:
        checks.extend(validate_suite_report(path))
    for path in manifests or []:
        checks.extend(validate_run_manifest(path))
    passed = sum(1 for check in checks if check.passed)
    return ArtifactValidationReport(
        total_checks=len(checks),
        passed_checks=passed,
        failed_checks=len(checks) - passed,
        checks=checks,
    )


def validate_benchmark_report(path: str | Path) -> list[ValidationCheck]:
    payload = _load_json(path)
    target = str(path)
    tasks = _tasks(payload)
    total = len(tasks)
    resolved = sum(1 for task in tasks if bool(task.get("resolved", False)))
    failure_types = dict(sorted(Counter(str(task.get("failure_type", "")) for task in tasks).items()))
    return [
        _check(
            "benchmark_report",
            target,
            "total_matches_tasks",
            int(payload.get("total", -1)) == total,
            f"declared={payload.get('total')} computed={total}",
        ),
        _check(
            "benchmark_report",
            target,
            "resolved_matches_tasks",
            int(payload.get("resolved", -1)) == resolved,
            f"declared={payload.get('resolved')} computed={resolved}",
        ),
        _check(
            "benchmark_report",
            target,
            "resolved_rate_matches_tasks",
            _float_equal(float(payload.get("resolved_rate", -1)), _rate(resolved, total)),
            f"declared={payload.get('resolved_rate')} computed={_rate(resolved, total)}",
        ),
        _check(
            "benchmark_report",
            target,
            "failure_types_match_tasks",
            dict(payload.get("failure_types", {})) == failure_types,
            f"declared={payload.get('failure_types', {})} computed={failure_types}",
        ),
    ]


def validate_comparison_report(path: str | Path) -> list[ValidationCheck]:
    payload = _load_json(path)
    target = str(path)
    tasks = _tasks(payload)
    status_counts = Counter(str(task.get("status", "")) for task in tasks)
    base_count = sum(1 for task in tasks if task.get("base_resolved") is not None)
    candidate_count = sum(1 for task in tasks if task.get("candidate_resolved") is not None)
    base_resolved = sum(1 for task in tasks if task.get("base_resolved") is True)
    candidate_resolved = sum(1 for task in tasks if task.get("candidate_resolved") is True)
    common_tasks = sum(
        1
        for task in tasks
        if task.get("base_resolved") is not None
        and task.get("candidate_resolved") is not None
    )
    transitions = Counter(
        f"{task.get('base_failure_type')} -> {task.get('candidate_failure_type')}"
        for task in tasks
        if task.get("base_resolved") is not None
        and task.get("candidate_resolved") is not None
    )
    return [
        _check(
            "comparison_report",
            target,
            "base_total_matches_tasks",
            int(payload.get("base_total", -1)) == base_count,
            f"declared={payload.get('base_total')} computed={base_count}",
        ),
        _check(
            "comparison_report",
            target,
            "candidate_total_matches_tasks",
            int(payload.get("candidate_total", -1)) == candidate_count,
            f"declared={payload.get('candidate_total')} computed={candidate_count}",
        ),
        _check(
            "comparison_report",
            target,
            "common_tasks_match_tasks",
            int(payload.get("common_tasks", -1)) == common_tasks,
            f"declared={payload.get('common_tasks')} computed={common_tasks}",
        ),
        _check(
            "comparison_report",
            target,
            "resolved_counts_match_tasks",
            int(payload.get("base_resolved", -1)) == base_resolved
            and int(payload.get("candidate_resolved", -1)) == candidate_resolved
            and int(payload.get("delta_resolved", 0)) == candidate_resolved - base_resolved,
            (
                f"declared=({payload.get('base_resolved')}, "
                f"{payload.get('candidate_resolved')}, {payload.get('delta_resolved')}) "
                f"computed=({base_resolved}, {candidate_resolved}, "
                f"{candidate_resolved - base_resolved})"
            ),
        ),
        _check(
            "comparison_report",
            target,
            "status_counts_match_tasks",
            _status_fields(payload) == _expected_status_fields(status_counts),
            f"declared={_status_fields(payload)} computed={_expected_status_fields(status_counts)}",
        ),
        _check(
            "comparison_report",
            target,
            "failure_transitions_match_tasks",
            dict(payload.get("failure_transitions", {})) == dict(sorted(transitions.items())),
            f"declared={payload.get('failure_transitions', {})} computed={dict(sorted(transitions.items()))}",
        ),
    ]


def validate_suite_report(path: str | Path) -> list[ValidationCheck]:
    payload = _load_json(path)
    target = str(path)
    entries = list(payload.get("entries", []))
    entry_names = [str(entry.get("name", "")) for entry in entries]
    checks = [
        _check(
            "suite_report",
            target,
            "baseline_exists",
            str(payload.get("baseline", "")) in entry_names,
            f"baseline={payload.get('baseline')} entries={entry_names}",
        )
    ]
    for entry in entries:
        name = str(entry.get("name", ""))
        repo_breakdown = list(entry.get("repo_breakdown", []))
        repo_total = sum(int(repo.get("total", 0)) for repo in repo_breakdown)
        repo_resolved = sum(int(repo.get("resolved", 0)) for repo in repo_breakdown)
        failure_total = sum(int(count) for count in dict(entry.get("failure_types", {})).values())
        total = int(entry.get("total", -1))
        resolved = int(entry.get("resolved", -1))
        checks.extend(
            [
                _check(
                    "suite_report",
                    target,
                    f"{name}:repo_total_matches_entry",
                    repo_total == total,
                    f"declared={total} computed={repo_total}",
                ),
                _check(
                    "suite_report",
                    target,
                    f"{name}:repo_resolved_matches_entry",
                    repo_resolved == resolved,
                    f"declared={resolved} computed={repo_resolved}",
                ),
                _check(
                    "suite_report",
                    target,
                    f"{name}:resolved_rate_matches_entry",
                    _float_equal(float(entry.get("resolved_rate", -1)), _rate(resolved, total)),
                    f"declared={entry.get('resolved_rate')} computed={_rate(resolved, total)}",
                ),
                _check(
                    "suite_report",
                    target,
                    f"{name}:failure_types_sum_to_total",
                    failure_total == total,
                    f"declared_total={total} failure_total={failure_total}",
                ),
            ]
        )
    return checks


def validate_run_manifest(path: str | Path) -> list[ValidationCheck]:
    payload = _load_json(path)
    target = str(path)
    checks: list[ValidationCheck] = []
    metrics = dict(payload.get("metrics", {}))
    report_json = str(payload.get("report_json", ""))
    if report_json:
        report = load_report_json(report_json)
        expected_metrics = {
            "total": report.total,
            "resolved": report.resolved,
            "resolved_rate": round(report.resolved_rate, 6),
            "failure_types": report.failure_types,
        }
        actual_metrics = {
            "total": metrics.get("total"),
            "resolved": metrics.get("resolved"),
            "resolved_rate": metrics.get("resolved_rate"),
            "failure_types": metrics.get("failure_types"),
        }
        checks.append(
            _check(
                "run_manifest",
                target,
                "metrics_match_report_json",
                actual_metrics == expected_metrics,
                f"declared={actual_metrics} computed={expected_metrics}",
            )
        )
    for artifact in list(payload.get("artifacts", [])):
        checks.extend(_validate_manifest_artifact(target, dict(artifact)))
    return checks


def render_validation_markdown(
    report: ArtifactValidationReport,
    *,
    title: str = "RepoPilot-CL Artifact Validation",
) -> str:
    lines = [
        f"# {title}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Passed | {_yes_no(report.passed)} |",
        f"| Total Checks | {report.total_checks} |",
        f"| Passed Checks | {report.passed_checks} |",
        f"| Failed Checks | {report.failed_checks} |",
        "",
        "## Checks",
        "",
        "| Target Type | Path | Check | Passed | Message |",
        "|---|---|---|---:|---|",
    ]
    for check in report.checks:
        lines.append(
            (
                f"| `{check.target_type}` | `{check.path}` | `{check.check}` | "
                f"{_yes_no(check.passed)} | {_escape_table_text(check.message)} |"
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def write_validation_artifacts(
    report: ArtifactValidationReport,
    markdown_path: str | Path,
    json_path: str | Path | None = None,
    *,
    title: str = "RepoPilot-CL Artifact Validation",
) -> None:
    md_path = Path(markdown_path)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_validation_markdown(report, title=title), encoding="utf-8")
    if json_path is not None:
        path = Path(json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")


def _validate_manifest_artifact(target: str, artifact: dict[str, Any]) -> list[ValidationCheck]:
    path = str(artifact.get("path", ""))
    label = str(artifact.get("label", "artifact"))
    artifact_path = Path(path)
    exists = artifact_path.exists() and artifact_path.is_file()
    if not exists:
        return [
            _check(
                "run_manifest",
                target,
                f"{label}:artifact_exists",
                not bool(artifact.get("exists", False)),
                f"declared={artifact.get('exists')} computed=False path={path}",
            )
        ]
    data = artifact_path.read_bytes()
    expected_size = len(data)
    expected_hash = hashlib.sha256(data).hexdigest()
    return [
        _check(
            "run_manifest",
            target,
            f"{label}:artifact_exists",
            bool(artifact.get("exists", False)),
            f"declared={artifact.get('exists')} computed=True path={path}",
        ),
        _check(
            "run_manifest",
            target,
            f"{label}:size_matches",
            int(artifact.get("size_bytes", -1)) == expected_size,
            f"declared={artifact.get('size_bytes')} computed={expected_size}",
        ),
        _check(
            "run_manifest",
            target,
            f"{label}:sha256_matches",
            str(artifact.get("sha256", "")) == expected_hash,
            f"declared={artifact.get('sha256')} computed={expected_hash}",
        ),
    ]


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _tasks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(task) for task in payload.get("tasks", [])]


def _check(
    target_type: str,
    path: str,
    check: str,
    passed: bool,
    message: str,
) -> ValidationCheck:
    return ValidationCheck(
        target_type=target_type,
        path=path,
        check=check,
        passed=passed,
        message=message,
    )


def _status_fields(payload: dict[str, Any]) -> dict[str, int]:
    return {
        "gained_tasks": int(payload.get("gained_tasks", -1)),
        "lost_tasks": int(payload.get("lost_tasks", -1)),
        "still_resolved": int(payload.get("still_resolved", -1)),
        "still_unresolved": int(payload.get("still_unresolved", -1)),
        "base_only_tasks": int(payload.get("base_only_tasks", -1)),
        "candidate_only_tasks": int(payload.get("candidate_only_tasks", -1)),
    }


def _expected_status_fields(status_counts: Counter[str]) -> dict[str, int]:
    return {
        "gained_tasks": status_counts["gained"],
        "lost_tasks": status_counts["lost"],
        "still_resolved": status_counts["still_resolved"],
        "still_unresolved": status_counts["still_unresolved"],
        "base_only_tasks": status_counts["base_only"],
        "candidate_only_tasks": status_counts["candidate_only"],
    }


def _rate(resolved: int, total: int) -> float:
    return resolved / total if total else 0.0


def _float_equal(left: float, right: float, tolerance: float = 1e-6) -> bool:
    return abs(left - right) <= tolerance


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _escape_table_text(text: str) -> str:
    return text.replace("|", "\\|")
