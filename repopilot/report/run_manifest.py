from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform

from repopilot.report.benchmark_report import BenchmarkReport, load_report_json


@dataclass(frozen=True)
class ManifestArtifact:
    label: str
    path: str
    exists: bool
    size_bytes: int | None
    sha256: str | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BenchmarkRunManifest:
    name: str
    created_at_utc: str
    git_commit: str
    command: str
    dataset: str
    task_ids_file: str
    provider: str
    model: str
    report_json: str
    metrics: dict[str, object]
    artifacts: list[ManifestArtifact]
    notes: list[str]
    runtime: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "created_at_utc": self.created_at_utc,
            "git_commit": self.git_commit,
            "command": self.command,
            "dataset": self.dataset,
            "task_ids_file": self.task_ids_file,
            "provider": self.provider,
            "model": self.model,
            "report_json": self.report_json,
            "metrics": self.metrics,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "notes": self.notes,
            "runtime": self.runtime,
        }


def build_run_manifest(
    *,
    name: str,
    command: str,
    dataset: str,
    task_ids_file: str,
    provider: str,
    model: str,
    report_json: str,
    git_commit: str,
    artifacts: list[tuple[str, str]],
    notes: list[str] | None = None,
    created_at_utc: str | None = None,
) -> BenchmarkRunManifest:
    report = load_report_json(report_json)
    artifact_inputs = _dedupe_artifacts(
        [
            ("dataset", dataset),
            ("task_ids", task_ids_file),
            ("report_json", report_json),
            *artifacts,
        ]
    )
    return BenchmarkRunManifest(
        name=name,
        created_at_utc=created_at_utc or _utc_now(),
        git_commit=git_commit,
        command=command,
        dataset=dataset,
        task_ids_file=task_ids_file,
        provider=provider,
        model=model,
        report_json=report_json,
        metrics=_metrics_from_report(report),
        artifacts=[_artifact_digest(label, path) for label, path in artifact_inputs],
        notes=list(notes or []),
        runtime={
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
    )


def render_run_manifest_markdown(manifest: BenchmarkRunManifest) -> str:
    lines = [
        f"# Run Manifest: {manifest.name}",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Created UTC | `{manifest.created_at_utc}` |",
        f"| Git Commit | `{manifest.git_commit}` |",
        f"| Dataset | `{manifest.dataset}` |",
        f"| Task IDs | `{manifest.task_ids_file}` |",
        f"| Provider | `{manifest.provider}` |",
        f"| Model | `{manifest.model}` |",
        f"| Report JSON | `{manifest.report_json}` |",
        f"| Python | `{manifest.runtime.get('python', '')}` |",
        f"| Platform | `{manifest.runtime.get('platform', '')}` |",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key, value in manifest.metrics.items():
        if key == "failure_types":
            continue
        lines.append(f"| {key} | {value} |")
    lines.extend(
        [
            "",
            "## Failure Types",
            "",
            "| Failure Type | Tasks |",
            "|---|---:|",
        ]
    )
    for failure_type, count in manifest.metrics.get("failure_types", {}).items():
        lines.append(f"| `{failure_type}` | {count} |")
    lines.extend(
        [
            "",
            "## Command",
            "",
            "```bash",
            manifest.command,
            "```",
            "",
            "## Artifacts",
            "",
            "| Label | Path | Exists | Size Bytes | SHA256 |",
            "|---|---|---:|---:|---|",
        ]
    )
    for artifact in manifest.artifacts:
        lines.append(
            (
                f"| `{artifact.label}` | `{artifact.path}` | "
                f"{_yes_no(artifact.exists)} | "
                f"{artifact.size_bytes if artifact.size_bytes is not None else 'n/a'} | "
                f"`{artifact.sha256 or 'n/a'}` |"
            )
        )
    if manifest.notes:
        lines.extend(["", "## Notes", ""])
        for note in manifest.notes:
            lines.append(f"- {note}")
    return "\n".join(lines).rstrip() + "\n"


def write_run_manifest_artifacts(
    manifest: BenchmarkRunManifest,
    markdown_path: str | Path,
    json_path: str | Path | None = None,
) -> None:
    md_path = Path(markdown_path)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_run_manifest_markdown(manifest), encoding="utf-8")
    if json_path is not None:
        path = Path(json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")


def _metrics_from_report(report: BenchmarkReport) -> dict[str, object]:
    return {
        "total": report.total,
        "resolved": report.resolved,
        "resolved_rate": round(report.resolved_rate, 6),
        "avg_patch_lines": round(report.avg_patch_lines, 3),
        "avg_model_steps": round(report.avg_model_steps, 3),
        "avg_tool_steps": round(report.avg_tool_steps, 3),
        "avg_test_runs": round(report.avg_test_runs, 3),
        "model_error_tasks": report.model_error_tasks,
        "timeout_tasks": report.timeout_tasks,
        "failure_types": report.failure_types,
    }


def _artifact_digest(label: str, path: str) -> ManifestArtifact:
    artifact_path = Path(path)
    if not artifact_path.exists() or not artifact_path.is_file():
        return ManifestArtifact(
            label=label,
            path=path,
            exists=False,
            size_bytes=None,
            sha256=None,
        )
    data = artifact_path.read_bytes()
    return ManifestArtifact(
        label=label,
        path=path,
        exists=True,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )


def _dedupe_artifacts(artifacts: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    result: list[tuple[str, str]] = []
    for label, path in artifacts:
        key = (label, path)
        if key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"
