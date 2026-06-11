from __future__ import annotations

import hashlib
import re

from repopilot.memory.schema import MemoryRecord
from repopilot.trajectory.schema import Trajectory


def memory_from_trajectory(trajectory: Trajectory) -> MemoryRecord:
    """Distill one repair trajectory into a compact retrieval record."""

    touched_files = extract_touched_files(trajectory.final_patch)
    error_signature = extract_error_signature(trajectory)
    issue_summary = summarize_issue(trajectory.issue)
    patch_pattern = summarize_patch_pattern(
        trajectory.final_patch,
        touched_files,
        resolved=trajectory.resolved,
    )
    memory_id = stable_memory_id(
        trajectory.repo,
        trajectory.task_id,
        error_signature,
        trajectory.resolved,
    )
    return MemoryRecord(
        memory_id=memory_id,
        task_id=trajectory.task_id,
        repo=trajectory.repo,
        issue_summary=issue_summary,
        error_signature=error_signature,
        touched_files=touched_files,
        patch_pattern=patch_pattern,
        resolved=trajectory.resolved,
    )


def stable_memory_id(
    repo: str,
    task_id: str,
    error_signature: str,
    resolved: bool,
) -> str:
    raw = f"{repo}\n{task_id}\n{error_signature}\n{resolved}".encode("utf-8")
    return "mem-" + hashlib.sha1(raw).hexdigest()[:12]


def summarize_issue(issue: str, max_chars: int = 220) -> str:
    lines = [line.strip() for line in issue.splitlines() if line.strip()]
    summary = " ".join(lines) if lines else "No issue text."
    if len(summary) <= max_chars:
        return summary
    return summary[: max_chars - 3].rstrip() + "..."


def extract_touched_files(diff: str) -> list[str]:
    files: list[str] = []
    for line in diff.splitlines():
        if not line.startswith("diff --git "):
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        old_path = _strip_git_prefix(parts[2])
        new_path = _strip_git_prefix(parts[3])
        path = new_path if new_path != "/dev/null" else old_path
        if path and path not in files:
            files.append(path)
    return files


def extract_error_signature(trajectory: Trajectory, max_chars: int = 180) -> str:
    for step in trajectory.steps:
        if step.action != "verify_baseline":
            continue
        candidates = [
            str(step.metadata.get("error_summary", "")),
            str(step.metadata.get("stderr", "")),
            str(step.metadata.get("stdout", "")),
            step.observation,
        ]
        for candidate in candidates:
            signature = _extract_error_like_token(candidate)
            if signature:
                return signature[:max_chars]
        for candidate in candidates:
            first_line = _first_interesting_line(candidate)
            if first_line:
                return first_line[:max_chars]

    verifier_summary = str(trajectory.verifier.get("error_summary", ""))
    fallback = _extract_error_like_token(verifier_summary) or _first_interesting_line(
        verifier_summary
    )
    return fallback[:max_chars] if fallback else "no verifier error captured"


def summarize_patch_pattern(
    diff: str,
    touched_files: list[str],
    *,
    resolved: bool,
) -> str:
    if not diff.strip():
        return f"no patch generated; resolved={resolved}"

    added = 0
    removed = 0
    for line in diff.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1

    file_text = ", ".join(touched_files) if touched_files else "unknown files"
    return f"edit {file_text}; +{added}/-{removed}; resolved={resolved}"


def _strip_git_prefix(path: str) -> str:
    if path.startswith("a/") or path.startswith("b/"):
        return path[2:]
    return path


def _extract_error_like_token(text: str) -> str:
    patterns = [
        r"\b([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception))\b",
        r"FAILED\s+([^\s]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""


def _first_interesting_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("=") or stripped.startswith("-"):
            continue
        return stripped
    return ""
