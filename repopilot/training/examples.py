from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from repopilot.critic.failure import build_failure_hint, render_prompt_hint


@dataclass(frozen=True)
class TrainingExample:
    example_id: str
    objective: str
    task_id: str
    repo: str
    source: str
    resolved: bool
    failure_type: str
    issue: str
    baseline_signal: str
    final_signal: str
    action_trace: str
    changed_files: list[str]
    patch_lines: int
    model_steps: int
    tool_steps: int
    test_runs: int
    input_text: str
    target: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class TrainingDatasetSummary:
    examples: int
    critic_examples: int
    reranker_examples: int
    resolved_examples: int
    unresolved_examples: int
    failure_types: dict[str, int]
    repositories: dict[str, int]
    sources: list[str]
    output: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_training_examples(
    trajectory_paths: list[str | Path],
    *,
    objectives: set[str] | None = None,
    include_resolved: bool = True,
    include_unresolved: bool = True,
    include_empty_patch_reranker: bool = False,
    max_signal_chars: int = 1200,
    max_patch_chars: int = 6000,
) -> list[TrainingExample]:
    selected_objectives = objectives or {"critic", "reranker"}
    unknown_objectives = selected_objectives - {"critic", "reranker"}
    if unknown_objectives:
        raise ValueError(f"Unknown training objective(s): {sorted(unknown_objectives)}")
    examples: list[TrainingExample] = []
    for path in trajectory_paths:
        source = str(path)
        for trajectory in _load_trajectories(path):
            resolved = bool(trajectory.get("resolved", False))
            if resolved and not include_resolved:
                continue
            if not resolved and not include_unresolved:
                continue
            if "critic" in selected_objectives:
                examples.append(
                    critic_example_from_trajectory(
                        trajectory,
                        source=source,
                        max_signal_chars=max_signal_chars,
                    )
                )
            if "reranker" in selected_objectives:
                final_patch = str(trajectory.get("final_patch") or "")
                if final_patch.strip() or include_empty_patch_reranker:
                    examples.append(
                        reranker_example_from_trajectory(
                            trajectory,
                            source=source,
                            max_signal_chars=max_signal_chars,
                            max_patch_chars=max_patch_chars,
                        )
                    )
    return examples


def critic_example_from_trajectory(
    trajectory: dict[str, Any],
    *,
    source: str,
    max_signal_chars: int = 1200,
) -> TrainingExample:
    hint = build_failure_hint(trajectory)
    steps = list(trajectory.get("steps", []))
    issue = _trim(str(trajectory.get("issue", "")), max_signal_chars)
    baseline_signal = _trim(hint.baseline_error, max_signal_chars)
    final_signal = _trim(hint.last_failure, max_signal_chars)
    input_text = "\n".join(
        part
        for part in [
            f"Repository: {trajectory.get('repo', '')}",
            f"Issue: {issue}",
            f"Baseline signal: {baseline_signal}",
            f"Final signal: {final_signal}",
            f"Action trace: {_action_trace(steps)}",
        ]
        if part.strip()
    )
    target = {
        "resolved": bool(trajectory.get("resolved", False)),
        "failure_type": hint.failure_type,
        "focus_files": hint.focus_files,
        "suggested_queries": hint.suggested_queries,
        "avoid": hint.avoid,
        "next_steps": hint.next_steps,
        "prompt_hint": render_prompt_hint(hint),
    }
    return _example(
        trajectory,
        objective="critic",
        source=source,
        failure_type=hint.failure_type,
        baseline_signal=baseline_signal,
        final_signal=final_signal,
        input_text=input_text,
        target=target,
    )


def reranker_example_from_trajectory(
    trajectory: dict[str, Any],
    *,
    source: str,
    max_signal_chars: int = 1200,
    max_patch_chars: int = 6000,
) -> TrainingExample:
    hint = build_failure_hint(trajectory)
    final_patch = str(trajectory.get("final_patch") or "")
    patch_text = _trim(final_patch, max_patch_chars)
    baseline_signal = _trim(hint.baseline_error, max_signal_chars)
    final_signal = _trim(hint.last_failure, max_signal_chars)
    input_text = "\n".join(
        [
            f"Repository: {trajectory.get('repo', '')}",
            f"Issue: {_trim(str(trajectory.get('issue', '')), max_signal_chars)}",
            f"Baseline signal: {baseline_signal}",
            f"Candidate patch:\n{patch_text}",
        ]
    )
    target = {
        "resolved": bool(trajectory.get("resolved", False)),
        "failure_type": hint.failure_type,
        "regression": bool(_mapping(trajectory.get("verifier", {})).get("regression", False)),
        "patch_score_label": 1 if bool(trajectory.get("resolved", False)) else 0,
    }
    return _example(
        trajectory,
        objective="reranker",
        source=source,
        failure_type=hint.failure_type,
        baseline_signal=baseline_signal,
        final_signal=final_signal,
        input_text=input_text,
        target=target,
    )


def write_training_examples(
    examples: list[TrainingExample],
    output_path: str | Path,
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for example in examples:
            handle.write(json.dumps(example.to_dict(), ensure_ascii=False) + "\n")


def summarize_training_examples(
    examples: list[TrainingExample],
    *,
    output: str,
) -> TrainingDatasetSummary:
    return TrainingDatasetSummary(
        examples=len(examples),
        critic_examples=sum(1 for example in examples if example.objective == "critic"),
        reranker_examples=sum(1 for example in examples if example.objective == "reranker"),
        resolved_examples=sum(1 for example in examples if example.resolved),
        unresolved_examples=sum(1 for example in examples if not example.resolved),
        failure_types=dict(sorted(Counter(example.failure_type for example in examples).items())),
        repositories=dict(sorted(Counter(example.repo for example in examples).items())),
        sources=sorted(set(example.source for example in examples)),
        output=output,
    )


def render_training_summary_markdown(
    summary: TrainingDatasetSummary,
    *,
    title: str = "RepoPilot-CL Training Dataset Summary",
) -> str:
    lines = [
        f"# {title}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Examples | {summary.examples} |",
        f"| Critic Examples | {summary.critic_examples} |",
        f"| Reranker Examples | {summary.reranker_examples} |",
        f"| Resolved Examples | {summary.resolved_examples} |",
        f"| Unresolved Examples | {summary.unresolved_examples} |",
        "",
        f"Output: `{summary.output}`",
        "",
        "## Failure Types",
        "",
        "| Failure Type | Examples |",
        "|---|---:|",
    ]
    for failure_type, count in summary.failure_types.items():
        lines.append(f"| `{failure_type}` | {count} |")
    lines.extend(["", "## Repositories", "", "| Repository | Examples |", "|---|---:|"])
    for repo, count in summary.repositories.items():
        lines.append(f"| `{repo}` | {count} |")
    lines.extend(["", "## Sources", ""])
    for source in summary.sources:
        lines.append(f"- `{source}`")
    return "\n".join(lines).rstrip() + "\n"


def write_training_summary(
    summary: TrainingDatasetSummary,
    *,
    output_json: str | Path | None = None,
    output_md: str | Path | None = None,
    title: str = "RepoPilot-CL Training Dataset Summary",
) -> None:
    if output_json is not None:
        path = Path(output_json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(summary.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    if output_md is not None:
        path = Path(output_md)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_training_summary_markdown(summary, title=title), encoding="utf-8")


def _example(
    trajectory: dict[str, Any],
    *,
    objective: str,
    source: str,
    failure_type: str,
    baseline_signal: str,
    final_signal: str,
    input_text: str,
    target: dict[str, object],
) -> TrainingExample:
    steps = list(trajectory.get("steps", []))
    final_patch = str(trajectory.get("final_patch") or "")
    changed_files = _changed_files(final_patch)
    action_trace = _action_trace(steps)
    return TrainingExample(
        example_id=_stable_example_id(
            str(trajectory.get("task_id", "")),
            objective,
            source,
            resolved=bool(trajectory.get("resolved", False)),
            failure_type=failure_type,
            final_patch=final_patch,
            action_trace=action_trace,
        ),
        objective=objective,
        task_id=str(trajectory.get("task_id", "")),
        repo=str(trajectory.get("repo", "")),
        source=source,
        resolved=bool(trajectory.get("resolved", False)),
        failure_type=failure_type,
        issue=_trim(str(trajectory.get("issue", "")), 1600),
        baseline_signal=baseline_signal,
        final_signal=final_signal,
        action_trace=action_trace,
        changed_files=changed_files,
        patch_lines=len(final_patch.splitlines()),
        model_steps=sum(1 for step in steps if step.get("action") == "model_action"),
        tool_steps=sum(1 for step in steps if str(step.get("action", "")).startswith("tool:")),
        test_runs=_max_test_runs(steps),
        input_text=input_text,
        target=target,
    )


def _load_trajectories(path: str | Path) -> list[dict[str, Any]]:
    trajectories: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                trajectories.append(json.loads(line))
    return trajectories


def _action_trace(steps: list[dict[str, Any]]) -> str:
    return " -> ".join(str(step.get("action", "")) for step in steps if step.get("action"))


def _max_test_runs(steps: list[dict[str, Any]]) -> int:
    values = []
    for step in steps:
        metadata = step.get("metadata", {})
        if isinstance(metadata, dict) and isinstance(metadata.get("test_runs"), int):
            values.append(metadata["test_runs"])
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
            path = parts[3]
            if path.startswith(("a/", "b/")):
                path = path[2:]
            if path not in files:
                files.append(path)
    return files


def _stable_example_id(
    task_id: str,
    objective: str,
    source: str,
    *,
    resolved: bool,
    failure_type: str,
    final_patch: str,
    action_trace: str,
) -> str:
    patch_hash = hashlib.sha1(final_patch.encode("utf-8")).hexdigest()
    raw = "\n".join(
        [
            task_id,
            objective,
            source,
            str(resolved),
            failure_type,
            patch_hash,
            action_trace,
        ]
    ).encode("utf-8")
    return "train-" + hashlib.sha1(raw).hexdigest()[:16]


def _trim(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _mapping(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}
