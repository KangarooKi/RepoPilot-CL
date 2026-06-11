from __future__ import annotations

from dataclasses import asdict, dataclass

from repopilot.memory.schema import MemoryRecord


@dataclass(frozen=True)
class PatchScore:
    candidate_id: str
    pass_probability: float
    regression_risk: float = 0.0
    patch_quality: float = 0.0

    @property
    def final_score(self) -> float:
        return self.pass_probability + 0.1 * self.patch_quality - self.regression_risk

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["final_score"] = self.final_score
        return payload


class RuleBasedPatchReranker:
    """Simple baseline before training RepoPilot-Reranker."""

    def score(
        self,
        candidate_id: str,
        patch: str,
        *,
        issue: str = "",
        baseline_error: str = "",
        memories: list[MemoryRecord] | None = None,
    ) -> PatchScore:
        changed_lines = [
            line
            for line in patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        ]
        removed_lines = [
            line
            for line in patch.splitlines()
            if line.startswith("-") and not line.startswith("---")
        ]
        size_penalty = min(len(changed_lines) / 100.0, 0.5)
        hardcode_penalty = 0.3 if "assert" in patch.lower() else 0.0
        delete_only_penalty = 0.2 if removed_lines and not changed_lines else 0.0
        issue_terms = set(_tokens(issue))
        patch_terms = set(_tokens(patch))
        memory_terms = {
            term
            for memory in memories or []
            for term in _tokens(
                " ".join(
                    [
                        memory.issue_summary,
                        memory.error_signature,
                        " ".join(memory.touched_files),
                        memory.patch_pattern,
                    ]
                )
            )
        }
        issue_overlap_bonus = min(len(issue_terms & patch_terms) * 0.02, 0.15)
        memory_overlap_bonus = min(len(memory_terms & patch_terms) * 0.01, 0.1)
        baseline_bonus = 0.05 if baseline_error and any(
            token in patch_terms for token in _tokens(baseline_error)
        ) else 0.0
        pass_probability = (
            0.5
            + issue_overlap_bonus
            + memory_overlap_bonus
            + baseline_bonus
            - size_penalty
            - hardcode_penalty
            - delete_only_penalty
        )
        return PatchScore(
            candidate_id=candidate_id,
            pass_probability=max(0.0, min(1.0, pass_probability)),
            regression_risk=min(1.0, hardcode_penalty + delete_only_penalty),
            patch_quality=max(0.0, 1.0 - size_penalty),
        )


def _tokens(text: str) -> list[str]:
    return [
        token
        for token in "".join(
            character.lower() if character.isalnum() or character == "_" else " "
            for character in text
        ).split()
        if len(token) >= 3
    ]
