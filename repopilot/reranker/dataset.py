from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RerankerExample:
    task_id: str
    candidate_id: str
    issue: str
    failing_tests: str
    repo_context: str
    retrieved_memory: str
    candidate_patch: str
    trajectory_summary: str
    resolved: bool
    regression: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def examples_from_trajectory_payload(payload: dict[str, Any]) -> list[RerankerExample]:
    steps = list(payload.get("steps", []))
    baseline = _first_step(steps, "verify_baseline")
    retrieved_memory = _summarize_retrieved_memory(steps)
    repo_context = str(payload.get("repo", ""))
    trajectory_summary = summarize_trajectory_steps(steps)
    examples: list[RerankerExample] = []

    for step in steps:
        if step.get("action") != "verify_candidate":
            continue
        metadata = dict(step.get("metadata", {}))
        candidate_patch = str(metadata.get("candidate_patch", ""))
        if not candidate_patch.strip():
            continue
        examples.append(
            RerankerExample(
                task_id=str(payload.get("task_id", "")),
                candidate_id=str(metadata.get("candidate_id", "")),
                issue=str(payload.get("issue", "")),
                failing_tests=str(baseline.get("observation", "")),
                repo_context=repo_context,
                retrieved_memory=retrieved_memory,
                candidate_patch=candidate_patch,
                trajectory_summary=trajectory_summary,
                resolved=bool(metadata.get("resolved", False)),
                regression=bool(metadata.get("regression", False)),
            )
        )
    return examples


def load_reranker_examples(paths: list[str | Path]) -> list[RerankerExample]:
    examples: list[RerankerExample] = []
    for path in paths:
        trajectory_path = Path(path)
        with trajectory_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                examples.extend(examples_from_trajectory_payload(json.loads(line)))
    return examples


def write_reranker_examples(
    examples: list[RerankerExample],
    output_path: str | Path,
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for example in examples:
            handle.write(json.dumps(example.to_dict(), ensure_ascii=False) + "\n")


def summarize_trajectory_steps(steps: list[dict[str, Any]]) -> str:
    actions = [str(step.get("action", "")) for step in steps if step.get("action")]
    return " -> ".join(actions)


def _first_step(steps: list[dict[str, Any]], action: str) -> dict[str, Any]:
    for step in steps:
        if step.get("action") == action:
            return step
    return {}


def _summarize_retrieved_memory(steps: list[dict[str, Any]]) -> str:
    step = _first_step(steps, "retrieve_memory")
    if not step:
        return ""
    metadata = dict(step.get("metadata", {}))
    memory_ids = metadata.get("memory_ids", [])
    if not memory_ids:
        return ""
    return "memory_ids=" + ",".join(str(memory_id) for memory_id in memory_ids)
