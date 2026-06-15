from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
import random
import re
from pathlib import Path
from typing import Any


CRITIC_SYSTEM_PROMPT = (
    "You are RepoPilot-Test-Time-Critic. Given a repository issue, verifier "
    "signals, and the current repair trace, output only valid JSON with these "
    "keys: failure_type, focus_files, suggested_queries, avoid, next_steps. "
    "The advice must guide the next repair attempt without writing the patch."
)


@dataclass(frozen=True)
class CriticSFTExample:
    example_id: str
    source_kind: str
    task_id: str
    repo: str
    input_text: str
    target: dict[str, object]
    messages: list[dict[str, str]]
    metadata: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CriticSFTSummary:
    examples: int
    source_kinds: dict[str, int]
    failure_types: dict[str, int]
    repositories: dict[str, int]
    splits: dict[str, int]
    output: str
    split_output_dir: str | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def swebench_record_to_critic_sft(
    record: dict[str, Any],
    *,
    source: str,
    max_issue_chars: int = 4000,
    max_tests: int = 12,
    max_focus_files: int = 8,
) -> CriticSFTExample:
    repo = str(record.get("repo", ""))
    task_id = str(record.get("instance_id") or record.get("task_id") or "")
    issue = _trim(
        str(record.get("problem_statement") or record.get("issue") or ""),
        max_issue_chars,
    )
    fail_to_pass = _coerce_list(record.get("FAIL_TO_PASS") or record.get("fail_to_pass_tests"))
    pass_to_pass = _coerce_list(record.get("PASS_TO_PASS") or record.get("pass_to_pass_tests"))
    patch = str(record.get("patch") or "")
    focus_files = _changed_files_from_patch(patch)[:max_focus_files]
    suggested_queries = _suggested_queries(
        issue=issue,
        tests=fail_to_pass[:max_tests],
        focus_files=focus_files,
    )
    target = {
        "failure_type": "needs_repair",
        "focus_files": focus_files,
        "suggested_queries": suggested_queries,
        "avoid": [
            "Do not edit files unrelated to the failing behavior.",
            "Do not make broad rewrites before locating the failing test path.",
            "Do not stop before rerunning the target regression tests.",
        ],
        "next_steps": _warmstart_next_steps(focus_files, fail_to_pass),
    }
    input_text = "\n".join(
        [
            f"Repository: {repo}",
            f"Task ID: {task_id}",
            "Issue:",
            issue,
            "Failing tests:",
            _format_list(fail_to_pass[:max_tests]),
            "Regression tests:",
            _format_list(pass_to_pass[:max_tests]),
            (
                "Current trace: No agent trajectory is available. Predict a "
                "focused repair plan from the issue and test names only."
            ),
        ]
    )
    return _sft_example(
        source_kind="swebench_gold",
        task_id=task_id,
        repo=repo,
        input_text=input_text,
        target=target,
        metadata={
            "source": source,
            "created_at": record.get("created_at"),
            "version": record.get("version"),
            "focus_source": "gold_patch_changed_files",
            "fail_to_pass_count": len(fail_to_pass),
            "pass_to_pass_count": len(pass_to_pass),
        },
    )


def training_example_to_critic_sft(payload: dict[str, Any]) -> CriticSFTExample | None:
    if str(payload.get("objective", "")) != "critic":
        return None
    target_payload = payload.get("target", {})
    if not isinstance(target_payload, dict):
        target_payload = {}
    resolved = bool(payload.get("resolved", False))
    target = {
        "failure_type": str(target_payload.get("failure_type") or payload.get("failure_type") or ""),
        "focus_files": _clean_focus_files(target_payload.get("focus_files", [])),
        "suggested_queries": [
            _sanitize_paths(str(item)) for item in target_payload.get("suggested_queries", [])
        ],
        "avoid": [_sanitize_paths(str(item)) for item in target_payload.get("avoid", [])],
        "next_steps": [
            _sanitize_paths(str(item)) for item in target_payload.get("next_steps", [])
        ],
    }
    if resolved or target["failure_type"] == "resolved":
        target = _resolved_target(target)
    return _sft_example(
        source_kind="repopilot_trajectory",
        task_id=str(payload.get("task_id", "")),
        repo=str(payload.get("repo", "")),
        input_text=_sanitize_paths(str(payload.get("input_text", ""))),
        target=target,
        metadata={
            "source": payload.get("source", ""),
            "resolved": resolved,
            "baseline_signal_chars": len(str(payload.get("baseline_signal", ""))),
            "final_signal_chars": len(str(payload.get("final_signal", ""))),
            "model_steps": int(payload.get("model_steps", 0) or 0),
            "tool_steps": int(payload.get("tool_steps", 0) or 0),
            "test_runs": int(payload.get("test_runs", 0) or 0),
        },
    )


def load_critic_sft_from_training_examples(
    paths: list[str | Path],
    *,
    max_examples: int | None = None,
) -> list[CriticSFTExample]:
    examples: list[CriticSFTExample] = []
    for path in paths:
        with Path(path).open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                example = training_example_to_critic_sft(json.loads(line))
                if example is None:
                    continue
                examples.append(example)
                if max_examples is not None and len(examples) >= max_examples:
                    return examples
    return examples


def load_critic_sft_from_swebench(
    paths: list[str | Path],
    *,
    exclude_task_ids: set[str] | None = None,
    max_records: int | None = None,
) -> list[CriticSFTExample]:
    examples: list[CriticSFTExample] = []
    for path in paths:
        source = str(path)
        with Path(path).open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                task_id = str(record.get("instance_id") or record.get("task_id") or "")
                if exclude_task_ids is not None and task_id in exclude_task_ids:
                    continue
                examples.append(swebench_record_to_critic_sft(record, source=source))
                if max_records is not None and len(examples) >= max_records:
                    return examples
    return examples


def split_critic_sft_by_task(
    examples: list[CriticSFTExample],
    *,
    train_ratio: float = 0.7,
    dev_ratio: float = 0.15,
    seed: int = 13,
) -> dict[str, list[CriticSFTExample]]:
    if train_ratio <= 0 or dev_ratio < 0 or train_ratio + dev_ratio >= 1:
        raise ValueError("Expected train_ratio > 0, dev_ratio >= 0, and train+dev < 1.")
    task_ids = sorted({example.task_id for example in examples})
    rng = random.Random(seed)
    rng.shuffle(task_ids)
    train_count = int(len(task_ids) * train_ratio)
    dev_count = int(len(task_ids) * dev_ratio)
    if len(task_ids) >= 3:
        train_count = max(1, train_count)
        dev_count = max(1, dev_count)
        if train_count + dev_count >= len(task_ids):
            dev_count = max(0, len(task_ids) - train_count - 1)
    train_tasks = set(task_ids[:train_count])
    dev_tasks = set(task_ids[train_count : train_count + dev_count])
    grouped = {"train": [], "dev": [], "test": []}
    for example in examples:
        if example.task_id in train_tasks:
            grouped["train"].append(example)
        elif example.task_id in dev_tasks:
            grouped["dev"].append(example)
        else:
            grouped["test"].append(example)
    return grouped


def write_critic_sft_jsonl(
    examples: list[CriticSFTExample],
    output_path: str | Path,
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for example in examples:
            handle.write(json.dumps(example.to_dict(), ensure_ascii=False) + "\n")


def write_critic_sft_splits(
    splits: dict[str, list[CriticSFTExample]],
    output_dir: str | Path,
) -> dict[str, str]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    for split, examples in splits.items():
        path = output_root / f"critic_{split}.jsonl"
        write_critic_sft_jsonl(examples, path)
        paths[split] = str(path)
    return paths


def summarize_critic_sft(
    examples: list[CriticSFTExample],
    *,
    output: str,
    split_output_dir: str | None = None,
    splits: dict[str, list[CriticSFTExample]] | None = None,
) -> CriticSFTSummary:
    split_counts = {
        name: len(items)
        for name, items in (splits or {}).items()
        if name in {"train", "dev", "test"}
    }
    return CriticSFTSummary(
        examples=len(examples),
        source_kinds=dict(sorted(Counter(example.source_kind for example in examples).items())),
        failure_types=dict(
            sorted(Counter(str(example.target.get("failure_type", "")) for example in examples).items())
        ),
        repositories=dict(sorted(Counter(example.repo for example in examples).items())),
        splits=split_counts,
        output=output,
        split_output_dir=split_output_dir,
    )


def write_critic_sft_summary(
    summary: CriticSFTSummary,
    *,
    output_json: str | Path | None = None,
    output_md: str | Path | None = None,
    title: str = "RepoPilot Critic SFT Dataset",
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
        path.write_text(render_critic_sft_summary(summary, title=title), encoding="utf-8")


def render_critic_sft_summary(
    summary: CriticSFTSummary,
    *,
    title: str = "RepoPilot Critic SFT Dataset",
) -> str:
    lines = [
        f"# {title}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Examples | {summary.examples} |",
        "",
        f"Output: `{summary.output}`",
    ]
    if summary.split_output_dir:
        lines.append(f"Split output dir: `{summary.split_output_dir}`")
    lines.extend(["", "## Source Kinds", "", "| Source | Examples |", "|---|---:|"])
    for source_kind, count in summary.source_kinds.items():
        lines.append(f"| `{source_kind}` | {count} |")
    lines.extend(["", "## Failure Types", "", "| Failure Type | Examples |", "|---|---:|"])
    for failure_type, count in summary.failure_types.items():
        lines.append(f"| `{failure_type}` | {count} |")
    if summary.splits:
        lines.extend(["", "## Splits", "", "| Split | Examples |", "|---|---:|"])
        for split, count in summary.splits.items():
            lines.append(f"| `{split}` | {count} |")
    lines.extend(["", "## Repositories", "", "| Repository | Examples |", "|---|---:|"])
    for repo, count in summary.repositories.items():
        lines.append(f"| `{repo}` | {count} |")
    return "\n".join(lines).rstrip() + "\n"


def load_task_ids(path: str | Path) -> set[str]:
    return {
        line.strip()
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def _sft_example(
    *,
    source_kind: str,
    task_id: str,
    repo: str,
    input_text: str,
    target: dict[str, object],
    metadata: dict[str, object],
) -> CriticSFTExample:
    assistant_content = json.dumps(target, ensure_ascii=False, sort_keys=True)
    messages = [
        {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
        {"role": "user", "content": input_text},
        {"role": "assistant", "content": assistant_content},
    ]
    example_id = _stable_example_id(source_kind, task_id, input_text, assistant_content)
    return CriticSFTExample(
        example_id=example_id,
        source_kind=source_kind,
        task_id=task_id,
        repo=repo,
        input_text=input_text,
        target=target,
        messages=messages,
        metadata=metadata,
    )


def _warmstart_next_steps(focus_files: list[str], fail_to_pass: list[str]) -> list[str]:
    steps = []
    if focus_files:
        steps.append("Inspect the files most likely touched by the repair: " + ", ".join(focus_files[:3]) + ".")
    else:
        steps.append("Search the repository for identifiers from the issue and failing tests.")
    if fail_to_pass:
        steps.append("Run the target failing tests after a minimal change: " + "; ".join(fail_to_pass[:3]) + ".")
    else:
        steps.append("Identify the smallest regression test that exercises the reported behavior.")
    steps.append("Keep the patch narrow and verify that existing passing tests do not regress.")
    return steps


def _resolved_target(target: dict[str, object]) -> dict[str, object]:
    focus_files = [str(item) for item in target.get("focus_files", [])]
    suggested_queries = [str(item) for item in target.get("suggested_queries", [])]
    file_hint = ", ".join(focus_files[:3]) if focus_files else "the localized repair files"
    query_hint = ", ".join(suggested_queries[:3]) if suggested_queries else "the failing symbols"
    return {
        "failure_type": "resolved",
        "focus_files": focus_files,
        "suggested_queries": suggested_queries,
        "avoid": [
            "Do not broaden a working minimal patch beyond the localized behavior.",
            "Do not discard verifier-confirmed focus files when solving related issues.",
        ],
        "next_steps": [
            f"Reuse the successful localization pattern around {file_hint}.",
            f"For related failures, search for {query_hint} and rerun the narrow target tests first.",
            "Preserve the minimal patch shape and check regression tests before submitting.",
        ],
    }


def _suggested_queries(
    *,
    issue: str,
    tests: list[str],
    focus_files: list[str],
    limit: int = 8,
) -> list[str]:
    queries: list[str] = []
    for test in tests:
        queries.extend(_identifier_terms(test))
    for path in focus_files:
        queries.extend(_identifier_terms(Path(path).stem))
    first_lines = "\n".join(issue.splitlines()[:8])
    queries.extend(_identifier_terms(first_lines))
    return _unique_nonempty(queries, limit=limit)


def _identifier_terms(text: str) -> list[str]:
    terms: list[str] = []
    for match in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", text):
        lowered = match.lower()
        if lowered in _STOPWORDS:
            continue
        terms.append(match)
    return terms


def _changed_files_from_patch(patch: str) -> list[str]:
    files: list[str] = []
    for line in patch.splitlines():
        if not line.startswith("diff --git "):
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        path = parts[3]
        if path.startswith(("a/", "b/")):
            path = path[2:]
        if path not in files:
            files.append(path)
    return files


def _coerce_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
        return [value]
    return [str(value)]


def _format_list(values: list[str]) -> str:
    if not values:
        return "- n/a"
    return "\n".join(f"- {value}" for value in values)


def _unique_nonempty(values: list[str], *, limit: int) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        value = value.strip()
        key = value.lower()
        if not value or key in seen:
            continue
        seen.add(key)
        result.append(value)
        if len(result) >= limit:
            break
    return result


def _stable_example_id(
    source_kind: str,
    task_id: str,
    input_text: str,
    assistant_content: str,
) -> str:
    raw = "\n".join([source_kind, task_id, input_text, assistant_content]).encode("utf-8")
    return "critic-" + hashlib.sha1(raw).hexdigest()[:16]


def _trim(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _sanitize_paths(text: str) -> str:
    text = re.sub(r"/Users/[^\s\"']+/RepoPilot-CL/", "<repopilot-workspace>/", text)
    text = re.sub(r"/Users/leiboqi/[^\s\"']+", "<local-user-path>", text)
    text = re.sub(r"/private/tmp/[^\s\"']+", "<tmp-path>", text)
    return text


def _clean_focus_files(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    files: list[str] = []
    for value in values:
        item = str(value).strip()
        if not item:
            continue
        if "/Users/leiboqi/" in item or item.startswith("Users/leiboqi/"):
            continue
        item = _sanitize_paths(item)
        if item not in files:
            files.append(item)
    return files


_STOPWORDS = {
    "and",
    "are",
    "but",
    "can",
    "for",
    "from",
    "has",
    "have",
    "not",
    "the",
    "this",
    "that",
    "with",
    "when",
    "where",
}
