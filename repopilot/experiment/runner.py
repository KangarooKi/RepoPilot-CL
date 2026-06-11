from __future__ import annotations

import contextlib
import io
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from repopilot.cli.run_benchmark import main as run_benchmark_main


@dataclass(frozen=True)
class ExperimentVariant:
    name: str
    context_enabled: bool
    memory_enabled: bool
    reranker: str
    num_candidates: int


@dataclass(frozen=True)
class ExperimentVariantResult:
    variant: str
    context_enabled: bool
    memory_enabled: bool
    reranker: str
    num_candidates: int
    total: int
    resolved: int
    resolved_rate: float
    summary_path: str
    trajectory_path: str
    memory_path: str | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ExperimentResult:
    variants: list[ExperimentVariantResult]

    def to_dict(self) -> dict[str, object]:
        return {"variants": [variant.to_dict() for variant in self.variants]}


DEFAULT_VARIANTS = [
    ExperimentVariant(
        name="baseline",
        context_enabled=False,
        memory_enabled=False,
        reranker="none",
        num_candidates=1,
    ),
    ExperimentVariant(
        name="context",
        context_enabled=True,
        memory_enabled=False,
        reranker="none",
        num_candidates=1,
    ),
    ExperimentVariant(
        name="memory",
        context_enabled=True,
        memory_enabled=True,
        reranker="none",
        num_candidates=1,
    ),
    ExperimentVariant(
        name="memory_reranker",
        context_enabled=True,
        memory_enabled=True,
        reranker="rule",
        num_candidates=3,
    ),
]


def select_variants(
    names: list[str] | None,
    *,
    num_candidates: int = 3,
) -> list[ExperimentVariant]:
    known = {variant.name: variant for variant in DEFAULT_VARIANTS}
    selected_names = names or [variant.name for variant in DEFAULT_VARIANTS]
    variants: list[ExperimentVariant] = []
    for name in selected_names:
        if name not in known:
            allowed = ", ".join(sorted(known))
            raise ValueError(f"Unknown variant `{name}`. Allowed variants: {allowed}.")
        variant = known[name]
        if variant.reranker != "none":
            variant = ExperimentVariant(
                name=variant.name,
                context_enabled=variant.context_enabled,
                memory_enabled=variant.memory_enabled,
                reranker=variant.reranker,
                num_candidates=num_candidates,
            )
        variants.append(variant)
    return variants


def run_experiment(
    *,
    tasks: list[str],
    common_args: list[str],
    output_dir: str | Path,
    variants: list[ExperimentVariant],
    run_benchmark: Callable[[list[str]], int] = run_benchmark_main,
) -> ExperimentResult:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    results: list[ExperimentVariantResult] = []

    for variant in variants:
        variant_dir = output_root / variant.name
        variant_dir.mkdir(parents=True, exist_ok=True)
        summary_path = variant_dir / "summary.json"
        trajectory_path = variant_dir / "trajectory.jsonl"
        memory_path = variant_dir / "memory.jsonl"
        runs_dir = variant_dir / "runs"
        for artifact_path in [summary_path, trajectory_path, memory_path]:
            if artifact_path.exists():
                artifact_path.unlink()

        argv = [
            *tasks,
            *common_args,
            "--runs-dir",
            str(runs_dir),
            "--trajectory-log",
            str(trajectory_path),
            "--output",
            str(summary_path),
            "--reranker",
            variant.reranker,
            "--num-candidates",
            str(variant.num_candidates),
        ]
        if variant.memory_enabled:
            argv.extend(["--memory-store", str(memory_path)])
        else:
            argv.append("--no-memory")
        if not variant.context_enabled:
            argv.append("--no-context")

        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = run_benchmark(argv)
        if exit_code != 0:
            raise RuntimeError(
                f"Variant `{variant.name}` failed with exit code {exit_code}."
            )
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        results.append(
            ExperimentVariantResult(
                variant=variant.name,
                context_enabled=variant.context_enabled,
                memory_enabled=variant.memory_enabled,
                reranker=variant.reranker,
                num_candidates=variant.num_candidates,
                total=int(summary["total"]),
                resolved=int(summary["resolved"]),
                resolved_rate=float(summary["resolved_rate"]),
                summary_path=str(summary_path),
                trajectory_path=str(trajectory_path),
                memory_path=str(memory_path) if variant.memory_enabled else None,
            )
        )

    return ExperimentResult(results)


def render_markdown_report(result: ExperimentResult) -> str:
    lines = [
        "# RepoPilot-CL Experiment Report",
        "",
        "| Variant | Context | Memory | Reranker | N | Resolved | Total | Rate |",
        "|---|---:|---:|---|---:|---:|---:|---:|",
    ]
    for variant in result.variants:
        lines.append(
            (
                f"| {variant.variant} | {_enabled_label(variant.context_enabled)} | "
                f"{_enabled_label(variant.memory_enabled)} | {variant.reranker} | "
                f"{variant.num_candidates} | {variant.resolved} | {variant.total} | "
                f"{variant.resolved_rate:.3f} |"
            )
        )
    lines.extend(
        [
            "",
            "Artifacts:",
        ]
    )
    for variant in result.variants:
        lines.append(
            f"- `{variant.variant}`: summary `{variant.summary_path}`, "
            f"trajectory `{variant.trajectory_path}`"
        )
    return "\n".join(lines) + "\n"


def _enabled_label(enabled: bool) -> str:
    return "on" if enabled else "off"
