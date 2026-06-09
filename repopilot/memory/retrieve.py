from __future__ import annotations

import re
from collections import Counter

from repopilot.memory.schema import MemoryRecord


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9_]+", text.lower())


class KeywordMemoryRetriever:
    """Small BM25-like retrieval baseline for MVP experiments."""

    def __init__(self, records: list[MemoryRecord]) -> None:
        self.records = records

    def retrieve(self, query: str, top_k: int = 3) -> list[MemoryRecord]:
        query_terms = Counter(tokenize(query))
        scored: list[tuple[float, MemoryRecord]] = []
        for record in self.records:
            text = " ".join(
                [
                    record.issue_summary,
                    record.error_signature,
                    " ".join(record.touched_files),
                    record.patch_pattern,
                ]
            )
            doc_terms = Counter(tokenize(text))
            score = sum(min(count, doc_terms.get(term, 0)) for term, count in query_terms.items())
            if score > 0:
                scored.append((float(score), record))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [record for _, record in scored[:top_k]]

