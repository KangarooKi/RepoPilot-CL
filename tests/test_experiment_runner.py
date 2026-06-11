import json
from pathlib import Path
import tempfile
import unittest

from repopilot.experiment.runner import (
    ExperimentVariant,
    render_markdown_report,
    run_experiment,
    select_variants,
)


class ExperimentRunnerTest(unittest.TestCase):
    def test_select_variants_overrides_reranker_candidate_count(self) -> None:
        variants = select_variants(["baseline", "memory_reranker"], num_candidates=5)

        self.assertEqual(
            [variant.name for variant in variants],
            ["baseline", "memory_reranker"],
        )
        self.assertEqual(variants[0].num_candidates, 1)
        self.assertEqual(variants[1].num_candidates, 5)

    def test_run_experiment_collects_variant_summaries(self) -> None:
        calls: list[list[str]] = []

        def fake_run_benchmark(argv: list[str]) -> int:
            calls.append(argv)
            output_path = Path(argv[argv.index("--output") + 1])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(
                    {
                        "total": 2,
                        "resolved": 1,
                        "resolved_rate": 0.5,
                        "tasks": [],
                    }
                ),
                encoding="utf-8",
            )
            return 0

        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_experiment(
                tasks=["tasks/toy/*/task.json"],
                common_args=["--provider", "scripted"],
                output_dir=temp_dir,
                variants=[
                    ExperimentVariant(
                        name="baseline",
                        memory_enabled=False,
                        reranker="none",
                        num_candidates=1,
                    ),
                    ExperimentVariant(
                        name="memory_reranker",
                        memory_enabled=True,
                        reranker="rule",
                        num_candidates=3,
                    ),
                ],
                run_benchmark=fake_run_benchmark,
            )

        self.assertEqual(
            [variant.variant for variant in result.variants],
            ["baseline", "memory_reranker"],
        )
        self.assertEqual(result.variants[0].resolved_rate, 0.5)
        self.assertIn("--no-memory", calls[0])
        self.assertIn("--memory-store", calls[1])
        self.assertEqual(calls[1][calls[1].index("--reranker") + 1], "rule")
        self.assertEqual(calls[1][calls[1].index("--num-candidates") + 1], "3")

    def test_render_markdown_report_contains_table(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_experiment(
                tasks=["tasks/toy/divide_by_zero/task.json"],
                common_args=["--provider", "scripted"],
                output_dir=temp_dir,
                variants=[
                    ExperimentVariant(
                        name="baseline",
                        memory_enabled=False,
                        reranker="none",
                        num_candidates=1,
                    )
                ],
                run_benchmark=_write_success_summary,
            )

        markdown = render_markdown_report(result)

        self.assertIn("| baseline | 1 | 1 | 1.000 |", markdown)
        self.assertIn("RepoPilot-CL Experiment Report", markdown)


def _write_success_summary(argv: list[str]) -> int:
    output_path = Path(argv[argv.index("--output") + 1])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "total": 1,
                "resolved": 1,
                "resolved_rate": 1.0,
                "tasks": [],
            }
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    unittest.main()
