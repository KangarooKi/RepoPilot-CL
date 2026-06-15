from __future__ import annotations

from collections import Counter
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from repopilot.report.benchmark_compare import compare_benchmark_reports
from repopilot.report.benchmark_report import BenchmarkReport


@dataclass(frozen=True)
class NamedBenchmarkReport:
    name: str
    path: str
    report: BenchmarkReport


@dataclass(frozen=True)
class RepoSuiteEntry:
    variant: str
    repo: str
    total: int
    resolved: int
    resolved_rate: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BenchmarkSuiteEntry:
    name: str
    path: str
    total: int
    resolved: int
    resolved_rate: float
    delta_resolved: int | None
    gained_tasks: int | None
    lost_tasks: int | None
    still_unresolved: int | None
    failure_types: dict[str, int]
    repo_breakdown: list[RepoSuiteEntry]

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "path": self.path,
            "total": self.total,
            "resolved": self.resolved,
            "resolved_rate": self.resolved_rate,
            "delta_resolved": self.delta_resolved,
            "gained_tasks": self.gained_tasks,
            "lost_tasks": self.lost_tasks,
            "still_unresolved": self.still_unresolved,
            "failure_types": self.failure_types,
            "repo_breakdown": [entry.to_dict() for entry in self.repo_breakdown],
        }


@dataclass(frozen=True)
class BenchmarkSuiteReport:
    title: str
    baseline: str
    entries: list[BenchmarkSuiteEntry]

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "baseline": self.baseline,
            "entries": [entry.to_dict() for entry in self.entries],
        }


def build_benchmark_suite(
    named_reports: list[NamedBenchmarkReport],
    *,
    title: str = "RepoPilot-CL Benchmark Suite",
    baseline_name: str | None = None,
    require_same_tasks: bool = False,
) -> BenchmarkSuiteReport:
    if not named_reports:
        raise ValueError("At least one benchmark report is required.")
    baseline = _select_baseline(named_reports, baseline_name)
    entries = [
        _build_suite_entry(
            named,
            baseline=baseline,
            require_same_tasks=require_same_tasks,
        )
        for named in named_reports
    ]
    return BenchmarkSuiteReport(title=title, baseline=baseline.name, entries=entries)


def render_suite_markdown(suite: BenchmarkSuiteReport) -> str:
    lines = [
        f"# {suite.title}",
        "",
        f"Baseline: `{suite.baseline}`",
        "",
        "## Variants",
        "",
        "| Variant | Tasks | Resolved | Rate | Delta | Gained | Lost | Still Unresolved | Failure Types |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for entry in suite.entries:
        lines.append(
            (
                f"| `{entry.name}` | {entry.total} | {entry.resolved} | "
                f"{entry.resolved_rate:.3f} | {_format_delta(entry.delta_resolved)} | "
                f"{_format_count(entry.gained_tasks)} | "
                f"{_format_count(entry.lost_tasks)} | "
                f"{_format_count(entry.still_unresolved)} | "
                f"{_format_failure_types(entry.failure_types)} |"
            )
        )
    lines.extend(
        [
            "",
            "## Repository Breakdown",
            "",
            "| Variant | Repository | Resolved | Total | Rate |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for entry in suite.entries:
        for repo_entry in entry.repo_breakdown:
            lines.append(
                (
                    f"| `{repo_entry.variant}` | `{repo_entry.repo}` | "
                    f"{repo_entry.resolved} | {repo_entry.total} | "
                    f"{repo_entry.resolved_rate:.3f} |"
                )
            )
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
        ]
    )
    for entry in suite.entries:
        lines.append(f"- `{entry.name}`: `{entry.path}`")
    return "\n".join(lines).rstrip() + "\n"


def write_suite_artifacts(
    suite: BenchmarkSuiteReport,
    markdown_path: str | Path,
    json_path: str | Path | None = None,
) -> None:
    md_path = Path(markdown_path)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_suite_markdown(suite), encoding="utf-8")
    if json_path is not None:
        path = Path(json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(suite.to_dict(), indent=2), encoding="utf-8")


def _build_suite_entry(
    named: NamedBenchmarkReport,
    *,
    baseline: NamedBenchmarkReport,
    require_same_tasks: bool,
) -> BenchmarkSuiteEntry:
    comparison = compare_benchmark_reports(
        baseline.report,
        named.report,
        base_name=baseline.name,
        candidate_name=named.name,
    )
    if require_same_tasks and (
        comparison.base_only_tasks or comparison.candidate_only_tasks
    ):
        raise ValueError(
            f"Report `{named.name}` does not have the same task ids as `{baseline.name}`."
        )
    return BenchmarkSuiteEntry(
        name=named.name,
        path=named.path,
        total=named.report.total,
        resolved=named.report.resolved,
        resolved_rate=named.report.resolved_rate,
        delta_resolved=comparison.delta_resolved,
        gained_tasks=comparison.gained_tasks,
        lost_tasks=comparison.lost_tasks,
        still_unresolved=comparison.still_unresolved,
        failure_types=named.report.failure_types,
        repo_breakdown=_repo_breakdown(named.name, named.report),
    )


def _select_baseline(
    named_reports: list[NamedBenchmarkReport],
    baseline_name: str | None,
) -> NamedBenchmarkReport:
    if baseline_name is None:
        return named_reports[0]
    for named in named_reports:
        if named.name == baseline_name:
            return named
    raise ValueError(f"Baseline report `{baseline_name}` was not provided.")


def _repo_breakdown(name: str, report: BenchmarkReport) -> list[RepoSuiteEntry]:
    totals = Counter(task.repo for task in report.tasks)
    resolved = Counter(task.repo for task in report.tasks if task.resolved)
    entries = [
        RepoSuiteEntry(
            variant=name,
            repo=repo,
            total=total,
            resolved=resolved[repo],
            resolved_rate=resolved[repo] / total if total else 0.0,
        )
        for repo, total in totals.items()
    ]
    return sorted(entries, key=lambda entry: (-entry.total, entry.repo))


def _format_delta(value: int | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:+d}" if value else "0"


def _format_count(value: int | None) -> str:
    return str(value) if value is not None else "n/a"


def _format_failure_types(failure_types: dict[str, int]) -> str:
    if not failure_types:
        return "none"
    return ", ".join(f"`{key}`={value}" for key, value in failure_types.items())
