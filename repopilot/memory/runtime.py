from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from repopilot.memory.distill import memory_from_trajectory
from repopilot.memory.retrieve import KeywordMemoryRetriever
from repopilot.memory.schema import MemoryRecord
from repopilot.memory.store import JsonlMemoryStore
from repopilot.trajectory.schema import Trajectory


@dataclass
class MemoryRuntime:
    store: JsonlMemoryStore | None
    records: list[MemoryRecord]
    top_k: int = 3

    @classmethod
    def disabled(cls) -> "MemoryRuntime":
        return cls(store=None, records=[])

    @classmethod
    def from_path(cls, path: str | Path, top_k: int = 3) -> "MemoryRuntime":
        store = JsonlMemoryStore(path)
        return cls(store=store, records=store.load(), top_k=top_k)

    def retriever(self) -> KeywordMemoryRetriever | None:
        if self.store is None:
            return None
        return KeywordMemoryRetriever(self.records, top_k=self.top_k)

    def learn(self, trajectory: Trajectory) -> MemoryRecord | None:
        if self.store is None:
            return None

        record = memory_from_trajectory(trajectory)
        self.store.upsert(record)
        self.records = [
            existing
            for existing in self.records
            if existing.memory_id != record.memory_id
        ]
        self.records.append(record)
        return record
