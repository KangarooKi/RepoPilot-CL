from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class RerankerExample:
    task_id: str
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

