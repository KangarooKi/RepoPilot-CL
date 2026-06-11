from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from repopilot.benchmark.task_loader import Task
from repopilot.memory.schema import MemoryRecord
from repopilot.sandbox.runner import SandboxRunner
from repopilot.tools.search import search_code


DEFAULT_STOPWORDS = {
    "and",
    "are",
    "but",
    "can",
    "for",
    "from",
    "have",
    "into",
    "not",
    "should",
    "test",
    "that",
    "the",
    "this",
    "when",
    "with",
}


@dataclass(frozen=True)
class ContextSnippet:
    path: str
    start_line: int
    end_line: int
    content: str
    score: float
    source: str


@dataclass(frozen=True)
class ContextPack:
    queries: list[str]
    snippets: list[ContextSnippet]

    def render(self) -> str:
        if not self.snippets:
            return "No repository context selected."
        blocks = []
        for snippet in self.snippets:
            blocks.append(
                "\n".join(
                    [
                        (
                            f"### {snippet.path}:{snippet.start_line}-"
                            f"{snippet.end_line} "
                            f"(score={snippet.score:.2f}, source={snippet.source})"
                        ),
                        "```text",
                        snippet.content,
                        "```",
                    ]
                )
            )
        return "\n\n".join(blocks)


class ContextPackBuilder:
    def __init__(
        self,
        *,
        max_queries: int = 8,
        max_snippets: int = 6,
        context_lines: int = 12,
        max_chars: int = 12000,
    ) -> None:
        self.max_queries = max_queries
        self.max_snippets = max_snippets
        self.context_lines = context_lines
        self.max_chars = max_chars

    def build(
        self,
        *,
        task: Task,
        workdir: Path,
        runner: SandboxRunner,
        memories: list[MemoryRecord],
    ) -> ContextPack:
        queries = select_queries(task, memories, max_queries=self.max_queries)
        snippets = self._inline_file_snippets(task, runner, workdir)
        snippets.extend(self._search_snippets(workdir, queries))
        ranked = sorted(snippets, key=lambda snippet: snippet.score, reverse=True)
        return ContextPack(
            queries=queries,
            snippets=_dedupe_and_trim(ranked, self.max_chars, self.max_snippets),
        )

    def _inline_file_snippets(
        self,
        task: Task,
        runner: SandboxRunner,
        workdir: Path,
    ) -> list[ContextSnippet]:
        snippets: list[ContextSnippet] = []
        for index, relative_path in enumerate(sorted(task.initial_files)):
            content = runner.read_file(workdir, relative_path)
            lines = content.splitlines()
            snippets.append(
                ContextSnippet(
                    path=relative_path,
                    start_line=1,
                    end_line=max(1, len(lines)),
                    content=_numbered_lines(lines, start_line=1),
                    score=100.0 - index,
                    source="initial_file",
                )
            )
        return snippets

    def _search_snippets(self, workdir: Path, queries: list[str]) -> list[ContextSnippet]:
        snippets: list[ContextSnippet] = []
        for query_index, query in enumerate(queries):
            for path, line_number, _line in search_code(workdir, query, limit=8):
                snippet = read_snippet(
                    workdir,
                    path,
                    line_number,
                    context_lines=self.context_lines,
                    score=50.0 - query_index,
                    source=f"query:{query}",
                )
                if snippet is not None:
                    snippets.append(snippet)
        return snippets


def select_queries(
    task: Task,
    memories: list[MemoryRecord],
    *,
    max_queries: int = 8,
) -> list[str]:
    weighted: dict[str, float] = {}

    def add(text: str, weight: float) -> None:
        for token in tokenize_query_text(text):
            weighted[token] = max(weighted.get(token, 0.0), weight)

    add(task.issue, 3.0)
    add(task.test_command, 2.0)
    add(" ".join(task.fail_to_pass_tests), 2.5)
    add(" ".join(task.pass_to_pass_tests), 1.5)
    for memory in memories:
        add(memory.error_signature, 2.5)
        add(" ".join(memory.touched_files), 2.0)
        add(memory.patch_pattern, 1.5)

    ranked = sorted(weighted.items(), key=lambda item: (-item[1], item[0]))
    return [token for token, _score in ranked[:max_queries]]


def tokenize_query_text(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", text)
    seen: set[str] = set()
    results: list[str] = []
    for token in tokens:
        normalized = token.lower()
        if normalized in DEFAULT_STOPWORDS or normalized in seen:
            continue
        seen.add(normalized)
        results.append(token)
    return results


def read_snippet(
    workdir: Path,
    relative_path: str,
    line_number: int,
    *,
    context_lines: int,
    score: float,
    source: str,
) -> ContextSnippet | None:
    path = workdir / relative_path
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return None
    if not lines:
        return None
    start = max(1, line_number - context_lines)
    end = min(len(lines), line_number + context_lines)
    selected = lines[start - 1 : end]
    return ContextSnippet(
        path=relative_path,
        start_line=start,
        end_line=end,
        content=_numbered_lines(selected, start_line=start),
        score=score,
        source=source,
    )


def _numbered_lines(lines: list[str], *, start_line: int) -> str:
    return "\n".join(
        f"{line_number}: {line}"
        for line_number, line in enumerate(lines, start=start_line)
    )


def _dedupe_and_trim(
    snippets: list[ContextSnippet],
    max_chars: int,
    max_snippets: int,
) -> list[ContextSnippet]:
    selected: list[ContextSnippet] = []
    seen_paths: set[str] = set()
    used_chars = 0
    for snippet in snippets:
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
