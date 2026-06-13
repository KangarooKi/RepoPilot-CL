from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FailureHint:
    task_id: str
    repo: str
    failure_type: str
    issue_title: str
    baseline_error: str
    last_failure: str
    focus_files: list[str]
    suggested_queries: list[str]
    avoid: list[str]
    next_steps: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_failure_hint(trajectory: dict[str, Any]) -> FailureHint:
    steps = list(trajectory.get("steps", []))
    final_patch = str(trajectory.get("final_patch") or "")
    resolved = bool(trajectory.get("resolved", False))
    issue = str(trajectory.get("issue", ""))
    failure_type = _failure_type(resolved, final_patch, steps)
    baseline_error = _baseline_error(steps)
    last_failure = _last_failure(steps, trajectory)
    focus_files = _focus_files(final_patch, steps, baseline_error, last_failure)
    suggested_queries = _suggested_queries(issue, baseline_error, last_failure, steps)
    avoid = _avoidance_rules(failure_type, steps, final_patch)
    next_steps = _next_steps(failure_type, focus_files, suggested_queries)
    return FailureHint(
        task_id=str(trajectory.get("task_id", "")),
        repo=str(trajectory.get("repo", "")),
        failure_type=failure_type,
        issue_title=_issue_title(issue),
        baseline_error=baseline_error,
        last_failure=last_failure,
        focus_files=focus_files,
        suggested_queries=suggested_queries,
        avoid=avoid,
        next_steps=next_steps,
    )


def load_failure_hints(
    path: str | Path,
) -> dict[str, FailureHint]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    items = payload.get("hints", payload if isinstance(payload, list) else [])
    hints: dict[str, FailureHint] = {}
    for item in items:
        hint = FailureHint(
            task_id=str(item.get("task_id", "")),
            repo=str(item.get("repo", "")),
            failure_type=str(item.get("failure_type", "")),
            issue_title=str(item.get("issue_title", "")),
            baseline_error=str(item.get("baseline_error", "")),
            last_failure=str(item.get("last_failure", "")),
            focus_files=[str(value) for value in item.get("focus_files", [])],
            suggested_queries=[str(value) for value in item.get("suggested_queries", [])],
            avoid=[str(value) for value in item.get("avoid", [])],
            next_steps=[str(value) for value in item.get("next_steps", [])],
        )
        if hint.task_id:
            hints[hint.task_id] = hint
    return hints


def load_prompt_hint_map(path: str | Path) -> dict[str, str]:
    return {
        task_id: render_prompt_hint(hint)
        for task_id, hint in load_failure_hints(path).items()
    }


def render_prompt_hint(hint: FailureHint) -> str:
    lines = [
        f"Previous failure type: {hint.failure_type}",
        f"Issue: {hint.issue_title or 'n/a'}",
    ]
    if hint.baseline_error:
        lines.append(f"Baseline signal: {_single_line(hint.baseline_error)}")
    if hint.last_failure:
        lines.append(f"Last failure signal: {_single_line(hint.last_failure)}")
    if hint.focus_files:
        lines.append("Focus files: " + ", ".join(hint.focus_files))
    if hint.suggested_queries:
        lines.append("Suggested searches: " + "; ".join(hint.suggested_queries))
    if hint.next_steps:
        lines.append("Next steps:")
        lines.extend(f"- {step}" for step in hint.next_steps)
    if hint.avoid:
        lines.append("Avoid:")
        lines.extend(f"- {rule}" for rule in hint.avoid)
    return "\n".join(lines)


def render_failure_hints_markdown(
    hints: list[FailureHint],
    *,
    title: str = "Failure Critic Hints",
    source: str | Path | None = None,
) -> str:
    lines = [f"# {title}", ""]
    if source is not None:
        lines.extend([f"- Source: `{source}`", ""])
    lines.extend(
        [
            "| Task | Failure Type | Focus Files | Suggested Searches |",
            "|---|---|---|---|",
        ]
    )
    for hint in hints:
        lines.append(
            (
                f"| `{hint.task_id}` | `{hint.failure_type}` | "
                f"{_format_list(hint.focus_files)} | {_format_list(hint.suggested_queries)} |"
            )
        )
    lines.append("")
    for hint in hints:
        lines.extend(
            [
                f"## `{hint.task_id}`",
                "",
                f"- Repository: `{hint.repo}`",
                f"- Issue: {hint.issue_title or 'n/a'}",
                f"- Previous failure type: `{hint.failure_type}`",
                f"- Baseline signal: {_single_line(hint.baseline_error) or 'n/a'}",
                f"- Last failure signal: {_single_line(hint.last_failure) or 'n/a'}",
                "",
                "Prompt hint:",
                "",
                "```text",
                render_prompt_hint(hint),
                "```",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def load_failed_trajectories(
    paths: list[str | Path],
    *,
    task_ids: set[str] | None = None,
    include_resolved: bool = False,
) -> list[dict[str, Any]]:
    trajectories: list[dict[str, Any]] = []
    for path in paths:
        with Path(path).open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                trajectory = json.loads(line)
                task_id = str(trajectory.get("task_id", ""))
                if task_ids is not None and task_id not in task_ids:
                    continue
                if not include_resolved and bool(trajectory.get("resolved", False)):
                    continue
                trajectories.append(trajectory)
    return trajectories


def _failure_type(
    resolved: bool,
    final_patch: str,
    steps: list[dict[str, Any]],
) -> str:
    if resolved:
        return "resolved"
    for step in steps:
        if step.get("action") == "model_call_error":
            observation = str(step.get("observation", ""))
            if "TimeoutError" in observation:
                return "model_timeout"
            return "model_call_error"
    if any(_tool_error(step) for step in steps):
        return "tool_error"
    if any(step.get("action") == "model_action_invalid" for step in steps):
        if not final_patch.strip():
            return "invalid_action_no_patch"
    if not final_patch.strip():
        return "no_patch"
    return "unresolved_patch"


def _baseline_error(steps: list[dict[str, Any]]) -> str:
    for step in steps:
        if step.get("action") != "verify_baseline":
            continue
        metadata = step.get("metadata", {})
        for key in ("error_summary", "stderr", "stdout"):
            value = str(metadata.get(key, "") if isinstance(metadata, dict) else "")
            if value.strip():
                return _trim(value)
        observation = str(step.get("observation", ""))
        if observation.strip():
            return _trim(observation)
    return ""


def _last_failure(
    steps: list[dict[str, Any]],
    trajectory: dict[str, Any],
) -> str:
    for step in reversed(steps):
        action = str(step.get("action", ""))
        if action in {"tool:run_tests", "tool:submit", "verify_final_unsubmitted_patch"}:
            metadata = step.get("metadata", {})
            if isinstance(metadata, dict):
                for key in ("error_summary", "stderr", "stdout"):
                    value = str(metadata.get(key, ""))
                    if value.strip():
                        return _trim(value)
            observation = str(step.get("observation", ""))
            if observation.strip():
                return _trim(observation)
        tool_error = _tool_error(step)
        if tool_error:
            return _trim(tool_error)
    verifier = trajectory.get("verifier", {})
    if isinstance(verifier, dict):
        for key in ("error_summary", "stderr", "stdout"):
            value = str(verifier.get(key, ""))
            if value.strip():
                return _trim(value)
    return ""


def _focus_files(
    final_patch: str,
    steps: list[dict[str, Any]],
    *texts: str,
) -> list[str]:
    files: list[str] = []
    files.extend(_changed_files(final_patch))
    for step in steps:
        metadata = step.get("metadata", {})
        action = metadata.get("action", {}) if isinstance(metadata, dict) else {}
        if not isinstance(action, dict):
            continue
        args = action.get("args", {})
        if not isinstance(args, dict):
            continue
        path = args.get("path")
        if isinstance(path, str):
            files.append(path)
    for text in texts:
        files.extend(_file_like_tokens(text))
    return _unique(files, limit=8)


def _suggested_queries(
    issue: str,
    baseline_error: str,
    last_failure: str,
    steps: list[dict[str, Any]],
) -> list[str]:
    queries: list[str] = []
    queries.extend(_error_tokens(baseline_error))
    queries.extend(_error_tokens(last_failure))
    queries.extend(_issue_terms(issue))
    for step in steps:
        metadata = step.get("metadata", {})
        action = metadata.get("action", {}) if isinstance(metadata, dict) else {}
        args = action.get("args", {}) if isinstance(action, dict) else {}
        query = args.get("query") if isinstance(args, dict) else None
        if isinstance(query, str) and query.strip():
            queries.append(query.strip())
    cleaned_queries = [
        query
        for query in (_clean_query(candidate) for candidate in queries)
        if query
    ]
    return _unique(cleaned_queries, limit=6)


def _avoidance_rules(
    failure_type: str,
    steps: list[dict[str, Any]],
    final_patch: str,
) -> list[str]:
    rules: list[str] = []
    if failure_type in {"no_patch", "invalid_action_no_patch"}:
        rules.append("Do not spend the full budget only reading files; make a minimal patch once the failure path is localized.")
    if failure_type == "unresolved_patch" or final_patch.strip():
        rules.append("Do not repeat the previous patch blindly; compare the final verifier output with the baseline failure first.")
    if any(step.get("action") == "model_action_invalid" for step in steps):
        rules.append("Return exactly one JSON tool action per turn, with no prose outside the JSON object.")
    if any(_tool_error(step) for step in steps):
        rules.append("Validate repository paths with search_code before read_file, replace_text, or apply_patch.")
    if any("Test budget exhausted" in str(step.get("observation", "")) for step in steps):
        rules.append("Run the narrow target test after each patch instead of spending test budget on broad suites.")
    if failure_type == "model_timeout":
        rules.append("Avoid broad exploration after a timeout; resume from the last inspected file and try a narrow edit.")
    return _unique(rules, limit=5)


def _next_steps(
    failure_type: str,
    focus_files: list[str],
    suggested_queries: list[str],
) -> list[str]:
    file_hint = focus_files[0] if focus_files else "the file surfaced by the failing stack trace"
    query_hint = suggested_queries[0] if suggested_queries else "the failing symbol or assertion text"
    if failure_type == "model_timeout":
        return [
            f"Start from `{file_hint}` and inspect only the function around the failing path.",
            "Apply one narrow edit, run the target pytest, then submit or revise based on verifier output.",
        ]
    if failure_type in {"no_patch", "invalid_action_no_patch"}:
        return [
            f"Search for `{query_hint}` and read the smallest matching implementation region.",
            "Turn the localized hypothesis into a minimal patch before the step budget is nearly exhausted.",
        ]
    if failure_type == "tool_error":
        return [
            f"Search for `{query_hint}` to recover the exact repository path before reading files.",
            "Retry the failed tool action only after confirming the path or symbol exists.",
        ]
    return [
        f"Inspect `{file_hint}` and the latest verifier output before editing.",
        "Patch the behavior that still fails the target test, not just compatibility warnings or nearby cleanup.",
    ]


def _changed_files(patch: str) -> list[str]:
    files: list[str] = []
    for line in patch.splitlines():
        if not line.startswith("diff --git "):
            continue
        parts = line.split()
        if len(parts) >= 4:
            files.append(_strip_git_prefix(parts[3]))
    return files


def _file_like_tokens(text: str) -> list[str]:
    return re.findall(r"\b[\w./-]+\.(?:py|sql|yaml|yml|toml|json|rst|md)\b", text)


def _error_tokens(text: str) -> list[str]:
    patterns = [
        r"\b[A-Za-z_][A-Za-z0-9_]*(?:Error|Exception)\b",
        r"FAILED\s+([^\s]+)",
        r"AssertionError[:\s]+([^\n]+)",
    ]
    tokens: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            token = match.group(1) if match.groups() else match.group(0)
            if pattern.startswith("FAILED") and "::" not in token and "/" not in token:
                continue
            tokens.append(_trim(token, max_chars=80))
    return tokens


def _issue_terms(issue: str) -> list[str]:
    terms: list[str] = []
    title = _issue_title(issue)
    for quoted in re.findall(r"`([^`]+)`|\"([^\"]+)\"", title):
        terms.extend(value for value in quoted if value)
    words = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{3,}\b", title)
    terms.extend(words[:4])
    return terms


def _clean_query(query: str) -> str:
    normalized = _trim(query, max_chars=100)
    if len(normalized) < 2:
        return ""
    lowered = normalized.lower()
    if lowered in {"console", "python", "version", "run"}:
        return ""
    if lowered.startswith("[") and lowered.endswith("]"):
        return ""
    if "traceback" in lowered or " file " in lowered:
        return ""
    return normalized


def _tool_error(step: dict[str, Any]) -> str:
    metadata = step.get("metadata", {})
    if not isinstance(metadata, dict):
        return ""
    return str(metadata.get("tool_error") or "")


def _issue_title(issue: str) -> str:
    for line in issue.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _strip_git_prefix(path: str) -> str:
    if path.startswith("a/") or path.startswith("b/"):
        return path[2:]
    return path


def _trim(text: str, max_chars: int = 400) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."


def _single_line(text: str) -> str:
    return _trim(text, max_chars=180)


def _format_list(items: list[str]) -> str:
    return ", ".join(f"`{item}`" for item in items) if items else "none"


def _unique(items: list[str], limit: int) -> list[str]:
    seen: set[str] = set()
    unique_items: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_items.append(normalized)
        if len(unique_items) >= limit:
            break
    return unique_items
