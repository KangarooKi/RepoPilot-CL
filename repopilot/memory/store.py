from __future__ import annotations

import json
from pathlib import Path

from repopilot.memory.schema import MemoryRecord


class JsonlMemoryStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: MemoryRecord) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

    def upsert(self, record: MemoryRecord) -> None:
        records = [
            existing
            for existing in self.load()
            if existing.memory_id != record.memory_id
        ]
        records.append(record)
        with self.path.open("w", encoding="utf-8") as handle:
            for item in records:
                handle.write(json.dumps(item.to_dict(), ensure_ascii=False) + "\n")

    def load(self) -> list[MemoryRecord]:
        if not self.path.exists():
            return []
        records: list[MemoryRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    records.append(MemoryRecord(**json.loads(line)))
        return records
