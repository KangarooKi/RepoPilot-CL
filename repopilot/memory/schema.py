from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class MemoryRecord:
    memory_id: str
    task_id: str
    repo: str
    issue_summary: str
    error_signature: str
    touched_files: list[str]
    patch_pattern: str
    resolved: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

