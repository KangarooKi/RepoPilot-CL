from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class TrajectoryStep:
    action: str
    observation: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Trajectory:
    task_id: str
    repo: str
    issue: str
    steps: list[TrajectoryStep] = field(default_factory=list)
    final_patch: str = ""
    resolved: bool = False
    verifier: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def add_step(
        self,
        action: str,
        observation: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.steps.append(TrajectoryStep(action, observation, metadata or {}))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["steps"] = [step.to_dict() for step in self.steps]
        return payload

