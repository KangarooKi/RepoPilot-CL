from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PatchScore:
    candidate_id: str
    pass_probability: float
    regression_risk: float = 0.0
    patch_quality: float = 0.0

    @property
    def final_score(self) -> float:
        return self.pass_probability + 0.1 * self.patch_quality - self.regression_risk


class RuleBasedPatchReranker:
    """Simple baseline before training RepoPilot-Reranker."""

    def score(self, candidate_id: str, patch: str) -> PatchScore:
        changed_lines = [
            line
            for line in patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        ]
        size_penalty = min(len(changed_lines) / 100.0, 0.5)
        hardcode_penalty = 0.3 if "assert" in patch.lower() else 0.0
        return PatchScore(
            candidate_id=candidate_id,
            pass_probability=max(0.0, 0.5 - size_penalty - hardcode_penalty),
            patch_quality=max(0.0, 1.0 - size_penalty),
        )

