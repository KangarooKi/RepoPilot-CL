from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from repopilot.memory.schema import MemoryRecord
from repopilot.reranker.dataset import RerankerExample
from repopilot.reranker.score import PatchScore


FEATURE_NAMES = [
    "added_frac",
    "removed_frac",
    "net_added_frac",
    "has_assert",
    "delete_only",
    "issue_overlap",
    "baseline_overlap",
    "memory_overlap",
]


@dataclass(frozen=True)
class TrainMetrics:
    examples: int
    positives: int
    negatives: int
    accuracy: float
    loss: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RerankerModel:
    feature_names: list[str]
    weights: dict[str, float]
    bias: float
    metrics: dict[str, object]

    def predict_probability(
        self,
        *,
        patch: str,
        issue: str = "",
        baseline_error: str = "",
        memory_text: str = "",
    ) -> float:
        features = extract_features(
            patch=patch,
            issue=issue,
            baseline_error=baseline_error,
            memory_text=memory_text,
        )
        logit = self.bias
        for feature_name in self.feature_names:
            logit += self.weights.get(feature_name, 0.0) * features.get(feature_name, 0.0)
        return _sigmoid(logit)

    def to_dict(self) -> dict[str, object]:
        return {
            "feature_names": self.feature_names,
            "weights": self.weights,
            "bias": self.bias,
            "metrics": self.metrics,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "RerankerModel":
        return cls(
            feature_names=[str(name) for name in payload["feature_names"]],
            weights={
                str(key): float(value)
                for key, value in dict(payload["weights"]).items()
            },
            bias=float(payload["bias"]),
            metrics=dict(payload.get("metrics", {})),
        )


class LearnedPatchReranker:
    def __init__(self, model: RerankerModel) -> None:
        self.model = model

    def score(
        self,
        candidate_id: str,
        patch: str,
        *,
        issue: str = "",
        baseline_error: str = "",
        memories: list[MemoryRecord] | None = None,
    ) -> PatchScore:
        memory_text = memories_to_text(memories or [])
        pass_probability = self.model.predict_probability(
            patch=patch,
            issue=issue,
            baseline_error=baseline_error,
            memory_text=memory_text,
        )
        features = extract_features(
            patch=patch,
            issue=issue,
            baseline_error=baseline_error,
            memory_text=memory_text,
        )
        regression_risk = min(
            1.0,
            0.25 * features["has_assert"] + 0.2 * features["delete_only"],
        )
        patch_quality = max(0.0, 1.0 - features["added_frac"])
        return PatchScore(
            candidate_id=candidate_id,
            pass_probability=pass_probability,
            regression_risk=regression_risk,
            patch_quality=patch_quality,
        )


def train_logistic_reranker(
    examples: list[RerankerExample],
    *,
    epochs: int = 200,
    learning_rate: float = 0.5,
    l2: float = 0.001,
) -> RerankerModel:
    if not examples:
        raise ValueError("Cannot train reranker with zero examples.")

    weights = {feature_name: 0.0 for feature_name in FEATURE_NAMES}
    bias = _initial_bias(examples)
    rows = [
        (
            extract_features(
                patch=example.candidate_patch,
                issue=example.issue,
                baseline_error=example.failing_tests,
                memory_text=example.retrieved_memory,
            ),
            1.0 if example.resolved and not example.regression else 0.0,
        )
        for example in examples
    ]

    for _ in range(epochs):
        for features, label in rows:
            prediction = _sigmoid(
                bias
                + sum(weights[name] * features.get(name, 0.0) for name in FEATURE_NAMES)
            )
            error = prediction - label
            bias -= learning_rate * error
            for name in FEATURE_NAMES:
                gradient = error * features.get(name, 0.0) + l2 * weights[name]
                weights[name] -= learning_rate * gradient

    metrics = evaluate_model(
        RerankerModel(
            feature_names=list(FEATURE_NAMES),
            weights=weights,
            bias=bias,
            metrics={},
        ),
        examples,
    )
    return RerankerModel(
        feature_names=list(FEATURE_NAMES),
        weights=weights,
        bias=bias,
        metrics=metrics.to_dict(),
    )


def evaluate_model(model: RerankerModel, examples: list[RerankerExample]) -> TrainMetrics:
    if not examples:
        return TrainMetrics(examples=0, positives=0, negatives=0, accuracy=0.0, loss=0.0)
    labels = [
        1.0 if example.resolved and not example.regression else 0.0
        for example in examples
    ]
    probabilities = [
        model.predict_probability(
            patch=example.candidate_patch,
            issue=example.issue,
            baseline_error=example.failing_tests,
            memory_text=example.retrieved_memory,
        )
        for example in examples
    ]
    correct = sum(
        1
        for probability, label in zip(probabilities, labels)
        if (probability >= 0.5) == bool(label)
    )
    loss = sum(
        _binary_log_loss(probability, label)
        for probability, label in zip(probabilities, labels)
    )
    positives = sum(1 for label in labels if label == 1.0)
    return TrainMetrics(
        examples=len(examples),
        positives=positives,
        negatives=len(examples) - positives,
        accuracy=correct / len(examples),
        loss=loss / len(examples),
    )


def extract_features(
    *,
    patch: str,
    issue: str = "",
    baseline_error: str = "",
    memory_text: str = "",
) -> dict[str, float]:
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
    patch_terms = set(_tokens(patch))
    issue_terms = set(_tokens(issue))
    baseline_terms = set(_tokens(baseline_error))
    memory_terms = set(_tokens(memory_text))
    return {
        "added_frac": min(len(changed_lines) / 100.0, 1.0),
        "removed_frac": min(len(removed_lines) / 100.0, 1.0),
        "net_added_frac": min(
            max(len(changed_lines) - len(removed_lines), 0) / 100.0,
            1.0,
        ),
        "has_assert": 1.0 if "assert" in patch.lower() else 0.0,
        "delete_only": 1.0 if removed_lines and not changed_lines else 0.0,
        "issue_overlap": min(len(issue_terms & patch_terms) / 10.0, 1.0),
        "baseline_overlap": min(len(baseline_terms & patch_terms) / 10.0, 1.0),
        "memory_overlap": min(len(memory_terms & patch_terms) / 10.0, 1.0),
    }


def memories_to_text(memories: list[MemoryRecord]) -> str:
    return " ".join(
        " ".join(
            [
                memory.issue_summary,
                memory.error_signature,
                " ".join(memory.touched_files),
                memory.patch_pattern,
            ]
        )
        for memory in memories
    )


def save_model(model: RerankerModel, path: str | Path) -> None:
    model_path = Path(path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_text(json.dumps(model.to_dict(), indent=2), encoding="utf-8")


def load_model(path: str | Path) -> RerankerModel:
    return RerankerModel.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def _tokens(text: str) -> list[str]:
    return [
        token
        for token in "".join(
            character.lower() if character.isalnum() or character == "_" else " "
            for character in text
        ).split()
        if len(token) >= 3
    ]


def _initial_bias(examples: list[RerankerExample]) -> float:
    positives = sum(
        1 for example in examples if example.resolved and not example.regression
    )
    positive_rate = min(max(positives / len(examples), 1e-3), 1.0 - 1e-3)
    return math.log(positive_rate / (1.0 - positive_rate))


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def _binary_log_loss(probability: float, label: float) -> float:
    clipped = min(max(probability, 1e-9), 1.0 - 1e-9)
    return -(label * math.log(clipped) + (1.0 - label) * math.log(1.0 - clipped))
