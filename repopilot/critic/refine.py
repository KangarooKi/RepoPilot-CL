from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re
from pathlib import Path
from typing import Any

from repopilot.context.pack import ContextSnippet, read_snippet
from repopilot.critic.distill import CRITIC_SYSTEM_PROMPT
from repopilot.critic.learned import normalize_critic_payload
from repopilot.tools.search import search_code


REFINEMENT_SYSTEM_PROMPT = (
    "You are RepoPilot-Test-Time-Critic in refinement mode. Given the original "
    "repository issue, a previous critic prediction, and repository search "
    "evidence, output only valid JSON with these keys: failure_type, focus_files, "
    "suggested_queries, avoid, next_steps. Revise focus_files when the evidence "
    "points to better repair locations. Do not write the patch."
)


@dataclass(frozen=True)
class RefinementEvidence:
    repo_root: str
    queries: list[str]
    snippets: list[ContextSnippet]
    missing_focus_files: list[str]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["snippets"] = [asdict(snippet) for snippet in self.snippets]
        return payload

    def render(self) -> str:
        lines = ["Repository evidence:"]
        lines.append("Queries used: " + _format_list_inline(self.queries))
        if self.missing_focus_files:
            lines.append(
                "Predicted focus files not found in repo: "
                + _format_list_inline(self.missing_focus_files)
            )
        if not self.snippets:
            lines.append("No repository snippets were retrieved.")
            return "\n".join(lines)
        for snippet in self.snippets:
            lines.extend(
                [
                    "",
                    (
                        f"### {snippet.path}:{snippet.start_line}-{snippet.end_line} "
                        f"(score={snippet.score:.2f}, source={snippet.source})"
                    ),
                    "```text",
                    snippet.content,
                    "```",
                ]
            )
        return "\n".join(lines)


@dataclass(frozen=True)
class RefinementSummary:
    examples: int
    with_repo_root: int
    with_snippets: int
    snippets: int
    output_jsonl: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class IndexedFile:
    path: str
    lines: list[str]


class RepositorySearchIndex:
    def __init__(self, root: str | Path, files: list[IndexedFile]) -> None:
        self.root = Path(root)
        self.files = files

    @classmethod
    def build(
        cls,
        root: str | Path,
        *,
        max_file_size: int = 250_000,
    ) -> "RepositorySearchIndex":
        root_path = Path(root)
        files: list[IndexedFile] = []
        for path in root_path.rglob("*"):
            if not path.is_file() or _skip_path(path):
                continue
            try:
                if path.stat().st_size > max_file_size:
                    continue
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            files.append(IndexedFile(path=str(path.relative_to(root_path)), lines=lines))
        return cls(root_path, files)

    def search(self, query: str, *, limit: int = 20) -> list[tuple[str, int, str]]:
        matches: list[tuple[str, int, str]] = []
        needle = query.lower()
        if not needle:
            return matches
        for file in self.files:
            for line_number, line in enumerate(file.lines, start=1):
                if needle in line.lower():
                    matches.append((file.path, line_number, line))
                    if len(matches) >= limit:
                        return matches
        return matches


def build_refinement_rows(
    prediction_rows: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
    *,
    repo_map: dict[str, str] | None = None,
    repo_root_template: str | None = None,
    max_examples: int | None = None,
    max_queries: int = 10,
    max_snippets: int = 8,
    context_lines: int = 12,
    max_evidence_chars: int = 12000,
    max_index_file_size: int = 250_000,
    max_neighbor_files: int = 4,
) -> list[dict[str, object]]:
    sources = source_row_map(source_rows)
    rows: list[dict[str, object]] = []
    indexes: dict[str, RepositorySearchIndex] = {}
    for prediction_row in prediction_rows:
        source_row = _lookup_source(prediction_row, sources)
        repo_root = resolve_repo_root(
            source_row or prediction_row,
            repo_map=repo_map,
            repo_root_template=repo_root_template,
        )
        search_index = _search_index_for(
            repo_root,
            indexes,
            max_file_size=max_index_file_size,
        )
        rows.append(
            build_refinement_row(
                prediction_row,
                source_row=source_row,
                repo_root=repo_root,
                search_index=search_index,
                max_queries=max_queries,
                max_snippets=max_snippets,
                context_lines=context_lines,
                max_evidence_chars=max_evidence_chars,
                max_neighbor_files=max_neighbor_files,
            )
        )
        if max_examples is not None and len(rows) >= max_examples:
            break
    return rows


def write_refinement_jsonl(
    rows: list[dict[str, object]],
    output_jsonl: str | Path,
) -> RefinementSummary:
    output_path = Path(output_jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return summarize_refinement_rows(rows, output_jsonl=str(output_path))


def summarize_refinement_rows(
    rows: list[dict[str, object]],
    *,
    output_jsonl: str,
) -> RefinementSummary:
    with_repo_root = 0
    with_snippets = 0
    snippet_count = 0
    for row in rows:
        metadata = row.get("metadata", {})
        if not isinstance(metadata, dict):
            continue
        evidence = metadata.get("refinement_evidence", {})
        if not isinstance(evidence, dict):
            continue
        if evidence.get("repo_root"):
            with_repo_root += 1
        snippets = evidence.get("snippets", [])
        if isinstance(snippets, list) and snippets:
            with_snippets += 1
            snippet_count += len(snippets)
    return RefinementSummary(
        examples=len(rows),
        with_repo_root=with_repo_root,
        with_snippets=with_snippets,
        snippets=snippet_count,
        output_jsonl=output_jsonl,
    )


def build_refinement_row(
    prediction_row: dict[str, Any],
    *,
    source_row: dict[str, Any] | None,
    repo_root: str | Path | None,
    search_index: RepositorySearchIndex | None = None,
    max_queries: int = 10,
    max_snippets: int = 8,
    context_lines: int = 12,
    max_evidence_chars: int = 12000,
    max_neighbor_files: int = 4,
) -> dict[str, object]:
    source = source_row or {}
    prediction = normalize_critic_payload(_coerce_mapping(prediction_row.get("prediction", {})))
    source_text = source_input_text(source) or source_input_text(prediction_row)
    evidence = collect_refinement_evidence(
        prediction=prediction,
        repo_root=repo_root,
        search_index=search_index,
        source_text=source_text,
        max_queries=max_queries,
        max_snippets=max_snippets,
        context_lines=context_lines,
        max_chars=max_evidence_chars,
        max_neighbor_files=max_neighbor_files,
    )
    input_text = build_refinement_input_text(
        source_text=source_text,
        prediction=prediction,
        evidence=evidence,
    )
    target = _target_payload(source, prediction_row)
    task_id = str(source.get("task_id") or prediction_row.get("task_id") or "")
    repo = str(source.get("repo") or prediction_row.get("repo") or "")
    example_id = str(source.get("example_id") or prediction_row.get("example_id") or task_id)
    assistant_content = json.dumps(target, ensure_ascii=False, sort_keys=True)
    return {
        "example_id": f"{example_id}-refine",
        "source_kind": "critic_refinement",
        "task_id": task_id,
        "repo": repo,
        "input_text": input_text,
        "target": target,
        "messages": [
            {"role": "system", "content": REFINEMENT_SYSTEM_PROMPT},
            {"role": "user", "content": input_text},
            {"role": "assistant", "content": assistant_content},
        ],
        "metadata": {
            "base_example_id": example_id,
            "base_valid_json": bool(prediction_row.get("valid_json", False)),
            "base_schema_valid": bool(prediction_row.get("schema_valid", False)),
            "base_prediction": prediction,
            "refinement_evidence": evidence.to_dict(),
        },
    }


def collect_refinement_evidence(
    *,
    prediction: dict[str, object],
    repo_root: str | Path | None,
    search_index: RepositorySearchIndex | None = None,
    source_text: str = "",
    max_queries: int = 10,
    max_snippets: int = 8,
    context_lines: int = 12,
    max_chars: int = 12000,
    max_neighbor_files: int = 4,
) -> RefinementEvidence:
    queries = build_refinement_queries(
        prediction,
        source_text=source_text,
        max_queries=max_queries,
    )
    if repo_root is None:
        return RefinementEvidence(
            repo_root="",
            queries=queries,
            snippets=[],
            missing_focus_files=[],
        )
    root = Path(repo_root)
    if not root.is_dir():
        return RefinementEvidence(
            repo_root=str(root),
            queries=queries,
            snippets=[],
            missing_focus_files=[],
        )

    snippets: list[ContextSnippet] = []
    missing_focus_files: list[str] = []
    for index, relative_path in enumerate(_focus_files(prediction)):
        path = root / relative_path
        if not path.is_file():
            missing_focus_files.append(relative_path)
            continue
        snippet = _focus_file_snippet(
            root,
            relative_path,
            queries,
            context_lines=context_lines,
            score=100.0 - index,
        )
        if snippet is not None:
            snippets.append(snippet)
        snippets.extend(
            _neighbor_file_snippets(
                root,
                relative_path,
                queries,
                context_lines=context_lines,
                score=78.0 - index,
                limit=max_neighbor_files,
            )
        )

    for query_index, query in enumerate(queries):
        matches = (
            search_index.search(query, limit=8)
            if search_index is not None
            else search_code(root, query, limit=8)
        )
        for path, line_number, _line in matches:
            snippet = read_snippet(
                root,
                path,
                line_number,
                context_lines=context_lines,
                score=70.0 - query_index,
                source=f"query:{query}",
            )
            if snippet is not None:
                snippets.append(snippet)

    return RefinementEvidence(
        repo_root=str(root),
        queries=queries,
        snippets=_dedupe_and_trim(snippets, max_chars=max_chars, max_snippets=max_snippets),
        missing_focus_files=missing_focus_files,
    )


def build_refinement_queries(
    prediction: dict[str, object],
    *,
    source_text: str = "",
    max_queries: int = 10,
) -> list[str]:
    normalized = normalize_critic_payload(prediction)
    candidates: list[str] = []
    candidates.extend(str(item) for item in normalized["suggested_queries"])
    for path in normalized["focus_files"]:
        path_text = str(path)
        candidates.extend(_identifier_terms(Path(path_text).stem))
        candidates.extend(_identifier_terms(path_text.replace("/", " ")))
    candidates.extend(_identifier_terms(source_text))
    return _unique_nonempty(candidates, limit=max_queries)


def refine_prediction_rows_with_evidence(
    prediction_rows: list[dict[str, Any]],
    refinement_rows: list[dict[str, Any]],
    *,
    max_focus_files: int = 8,
    keep_original: int = 1,
) -> list[dict[str, object]]:
    refined_rows: list[dict[str, object]] = []
    refinement_by_key = source_row_map(refinement_rows)
    for row in prediction_rows:
        refinement_row = _lookup_source(row, refinement_by_key)
        refined_rows.append(
            refine_prediction_row_with_evidence(
                row,
                refinement_row=refinement_row,
                max_focus_files=max_focus_files,
                keep_original=keep_original,
            )
        )
    return refined_rows


def refine_prediction_row_with_evidence(
    prediction_row: dict[str, Any],
    *,
    refinement_row: dict[str, Any] | None,
    max_focus_files: int = 8,
    keep_original: int = 1,
) -> dict[str, object]:
    prediction = normalize_critic_payload(_coerce_mapping(prediction_row.get("prediction", {})))
    evidence_paths = _evidence_paths(refinement_row or {})
    original_focus = [str(path) for path in prediction["focus_files"]]
    focus_files = _merge_focus_files(
        original_focus,
        evidence_paths,
        keep_original=keep_original,
        max_focus_files=max_focus_files,
    )
    refined_prediction = dict(prediction)
    refined_prediction["focus_files"] = focus_files
    output = dict(prediction_row)
    output["prediction"] = refined_prediction
    output["schema_valid"] = bool(prediction_row.get("schema_valid", True))
    output["valid_json"] = bool(prediction_row.get("valid_json", True))
    output["refinement_strategy"] = "retrieval_evidence_focus_expansion"
    output["metadata"] = {
        "base_prediction": prediction,
        "evidence_focus_files": evidence_paths,
        "keep_original": keep_original,
        "max_focus_files": max_focus_files,
    }
    return output


def write_prediction_rows_jsonl(
    rows: list[dict[str, object]],
    output_jsonl: str | Path,
) -> None:
    path = Path(output_jsonl)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_refinement_input_text(
    *,
    source_text: str,
    prediction: dict[str, object],
    evidence: RefinementEvidence,
) -> str:
    normalized_prediction = normalize_critic_payload(prediction)
    return "\n".join(
        [
            "Original critic input:",
            _trim(source_text, 6000) or "n/a",
            "",
            "Previous critic prediction:",
            json.dumps(normalized_prediction, ensure_ascii=False, indent=2),
            "",
            evidence.render(),
            "",
            "Refinement objective:",
            (
                "Revise the previous critic prediction using the repository evidence. "
                "Prioritize repository-relative focus_files that are directly supported "
                "by snippets, failing tests, or issue identifiers. Keep useful previous "
                "queries, add better ones when needed, and output only the JSON object."
            ),
        ]
    )


def source_row_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    mapped: dict[str, dict[str, Any]] = {}
    for row in rows:
        for key in _row_keys(row):
            mapped[key] = row
    return mapped


def source_input_text(row: dict[str, Any]) -> str:
    text = str(row.get("input_text") or "").strip()
    if text:
        return text
    messages = row.get("messages", [])
    if isinstance(messages, list):
        for message in messages:
            if not isinstance(message, dict):
                continue
            if str(message.get("role", "")) == "user":
                return str(message.get("content", "")).strip()
    return ""


def resolve_repo_root(
    row: dict[str, Any],
    *,
    repo_map: dict[str, str] | None = None,
    repo_root_template: str | None = None,
) -> str | None:
    task_id = str(row.get("task_id") or "").strip()
    repo = str(row.get("repo") or "").strip()
    repo_slug = repo.replace("/", "__")
    if repo_map:
        for key in (task_id, repo, repo_slug):
            if key and key in repo_map:
                return repo_map[key]
    local_repo_path = str(row.get("local_repo_path") or "").strip()
    if local_repo_path:
        return local_repo_path
    metadata = row.get("metadata", {})
    if isinstance(metadata, dict):
        metadata_path = str(metadata.get("local_repo_path") or "").strip()
        if metadata_path:
            return metadata_path
    if repo_root_template:
        return repo_root_template.format(task_id=task_id, repo=repo, repo_slug=repo_slug)
    return None


def load_repo_map(path: str | Path | None) -> dict[str, str]:
    if path is None:
        return {}
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Repository map must be a JSON object.")
    result: dict[str, str] = {}
    for key, value in payload.items():
        if key in {"repos", "tasks"} and isinstance(value, dict):
            for nested_key, nested_value in value.items():
                result[str(nested_key)] = str(nested_value)
        else:
            result[str(key)] = str(value)
    return result


def _search_index_for(
    repo_root: str | Path | None,
    indexes: dict[str, RepositorySearchIndex],
    *,
    max_file_size: int,
) -> RepositorySearchIndex | None:
    if repo_root is None:
        return None
    root = Path(repo_root)
    if not root.is_dir():
        return None
    key = str(root.resolve())
    if key not in indexes:
        indexes[key] = RepositorySearchIndex.build(
            root,
            max_file_size=max_file_size,
        )
    return indexes[key]


def _lookup_source(
    prediction_row: dict[str, Any],
    sources: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    for key in _row_keys(prediction_row):
        if key in sources:
            return sources[key]
    return None


def _row_keys(row: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for field in ("example_id", "task_id"):
        value = str(row.get(field) or "").strip()
        if value:
            keys.append(value)
    return keys


def _target_payload(
    source_row: dict[str, Any],
    prediction_row: dict[str, Any],
) -> dict[str, object]:
    for row, field in ((source_row, "target"), (prediction_row, "reference")):
        payload = row.get(field)
        if isinstance(payload, dict):
            return normalize_critic_payload(payload)
    return normalize_critic_payload({})


def _coerce_mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _focus_files(prediction: dict[str, object]) -> list[str]:
    normalized = normalize_critic_payload(prediction)
    return [str(path) for path in normalized["focus_files"]]


def _focus_file_snippet(
    root: Path,
    relative_path: str,
    queries: list[str],
    *,
    context_lines: int,
    score: float,
) -> ContextSnippet | None:
    path = root / relative_path
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return None
    match_line = 1
    lowered_queries = [query.lower() for query in queries if query]
    for line_number, line in enumerate(lines, start=1):
        lowered = line.lower()
        if any(query in lowered for query in lowered_queries):
            match_line = line_number
            break
    return read_snippet(
        root,
        relative_path,
        match_line,
        context_lines=context_lines,
        score=score,
        source="predicted_focus_file",
    )


def _neighbor_file_snippets(
    root: Path,
    relative_path: str,
    queries: list[str],
    *,
    context_lines: int,
    score: float,
    limit: int,
) -> list[ContextSnippet]:
    if limit <= 0:
        return []
    source_path = root / relative_path
    candidates: list[Path] = []
    if source_path.parent.is_dir():
        for suffix in (".py", ".pyi"):
            candidates.extend(sorted(source_path.parent.glob(f"*{suffix}")))
    candidates.extend(sorted(root.rglob(source_path.name)))
    selected: list[ContextSnippet] = []
    seen: set[str] = {relative_path}
    for candidate in sorted(
        candidates,
        key=lambda path: _neighbor_score(path, queries),
        reverse=True,
    ):
        if not candidate.is_file() or _skip_path(candidate):
            continue
        try:
            candidate_relative = str(candidate.relative_to(root))
        except ValueError:
            continue
        if candidate_relative in seen:
            continue
        seen.add(candidate_relative)
        snippet = _focus_file_snippet(
            root,
            candidate_relative,
            queries,
            context_lines=context_lines,
            score=score - len(selected) * 0.25,
        )
        if snippet is not None:
            selected.append(snippet)
        if len(selected) >= limit:
            break
    return selected


def _neighbor_score(path: Path, queries: list[str]) -> tuple[int, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        text = ""
    lowered = text.lower()
    hits = sum(1 for query in queries if query.lower() in lowered)
    return hits, str(path)


def _skip_path(path: Path) -> bool:
    skipped_parts = {
        ".git",
        ".hg",
        ".mypy_cache",
        ".pytest_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "site-packages",
    }
    return any(part in skipped_parts for part in path.parts)


def _evidence_paths(refinement_row: dict[str, Any]) -> list[str]:
    metadata = refinement_row.get("metadata", {})
    if not isinstance(metadata, dict):
        return []
    evidence = metadata.get("refinement_evidence", {})
    if not isinstance(evidence, dict):
        return []
    snippets = evidence.get("snippets", [])
    paths: list[str] = []
    seen: set[str] = set()
    if not isinstance(snippets, list):
        return []
    for snippet in snippets:
        if not isinstance(snippet, dict):
            continue
        path = str(snippet.get("path") or "").strip()
        if not path or path in seen:
            continue
        paths.append(path)
        seen.add(path)
    return paths


def _merge_focus_files(
    original_focus: list[str],
    evidence_focus: list[str],
    *,
    keep_original: int,
    max_focus_files: int,
) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()

    def add(path: str) -> None:
        path = path.strip()
        if path and path not in seen and len(merged) < max_focus_files:
            merged.append(path)
            seen.add(path)

    for path in original_focus[:keep_original]:
        add(path)
    for path in evidence_focus:
        add(path)
    for path in original_focus[keep_original:]:
        add(path)
    return merged


def _dedupe_and_trim(
    snippets: list[ContextSnippet],
    *,
    max_chars: int,
    max_snippets: int,
) -> list[ContextSnippet]:
    ranked = sorted(snippets, key=lambda snippet: snippet.score, reverse=True)
    selected: list[ContextSnippet] = []
    seen_paths: set[str] = set()
    used_chars = 0
    for snippet in ranked:
        if len(selected) >= max_snippets:
            break
        if snippet.path in seen_paths:
            continue
        snippet_size = len(snippet.content)
        if selected and used_chars + snippet_size > max_chars:
            continue
        selected.append(snippet)
        seen_paths.add(snippet.path)
        used_chars += snippet_size
    return selected


def _identifier_terms(text: str) -> list[str]:
    terms: list[str] = []
    for match in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", text):
        lowered = match.lower()
        if lowered in _STOPWORDS:
            continue
        terms.append(match)
    return terms


def _unique_nonempty(values: list[str], *, limit: int) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = re.sub(r"\s+", " ", str(value)).strip()
        key = text.lower()
        if not text or key in seen:
            continue
        result.append(text)
        seen.add(key)
        if len(result) >= limit:
            break
    return result


def _format_list_inline(values: list[str]) -> str:
    return ", ".join(values) if values else "n/a"


def _trim(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


_STOPWORDS = {
    "and",
    "are",
    "but",
    "can",
    "for",
    "from",
    "has",
    "have",
    "into",
    "not",
    "the",
    "this",
    "that",
    "with",
    "when",
    "where",
}
