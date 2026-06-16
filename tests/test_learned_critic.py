import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from repopilot.cli.build_learned_critic_hints import main as build_hints_main
from repopilot.cli.evaluate_critic import main as evaluate_main
from repopilot.critic.failure import load_prompt_hint_map
from repopilot.critic.learned import (
    evaluate_predictions,
    parse_critic_output,
    prediction_to_failure_hint,
)


class LearnedCriticTest(unittest.TestCase):
    def test_parse_critic_output_extracts_fenced_json(self) -> None:
        result = parse_critic_output(
            """
            Some preface.
            ```json
            {
              "failure_type": "needs_repair",
              "focus_files": ["a/src/pkg/parser.py"],
              "suggested_queries": ["parse_sequence"],
              "avoid": ["Do not rewrite the parser."],
              "next_steps": ["Inspect parser state."]
            }
            ```
            """
        )

        self.assertTrue(result.valid_json)
        self.assertTrue(result.schema_valid)
        self.assertEqual(result.prediction["focus_files"], ["src/pkg/parser.py"])

    def test_parse_critic_output_flags_schema_error(self) -> None:
        result = parse_critic_output('{"failure_type": "needs_repair"}')

        self.assertTrue(result.valid_json)
        self.assertFalse(result.schema_valid)
        self.assertEqual(result.error, "schema_invalid")

    def test_evaluate_predictions_scores_focus_recall_and_failure_type(self) -> None:
        rows = [
            {
                "task_id": "demo__repo-1",
                "valid_json": True,
                "schema_valid": True,
                "prediction": {
                    "failure_type": "needs_repair",
                    "focus_files": ["tests/test_parser.py", "src/pkg/parser.py"],
                    "suggested_queries": ["parse_sequence"],
                    "avoid": [],
                    "next_steps": ["Inspect parser state."],
                },
                "reference": {
                    "failure_type": "needs_repair",
                    "focus_files": ["src/pkg/parser.py"],
                    "suggested_queries": [],
                    "avoid": [],
                    "next_steps": [],
                },
            }
        ]

        summary = evaluate_predictions(rows, focus_ks=(1, 2))
        payload = summary.to_dict()

        self.assertEqual(payload["failure_type_accuracy"], 1.0)
        self.assertEqual(payload["focus_recall"]["recall@1"], 0.0)
        self.assertEqual(payload["focus_recall"]["recall@2"], 1.0)
        self.assertEqual(payload["focus_mrr"], 0.5)
        self.assertEqual(payload["query_nonempty_rate"], 1.0)
        self.assertEqual(payload["next_steps_nonempty_rate"], 1.0)

    def test_prediction_to_failure_hint_is_prompt_hint_compatible(self) -> None:
        hint = prediction_to_failure_hint(
            {
                "task_id": "demo__repo-1",
                "repo": "demo/repo",
                "prediction": {
                    "failure_type": "needs_repair",
                    "focus_files": ["src/pkg/parser.py"],
                    "suggested_queries": ["parse_sequence"],
                    "avoid": ["Avoid broad rewrites."],
                    "next_steps": ["Inspect parser state."],
                },
            }
        )

        self.assertEqual(hint.task_id, "demo__repo-1")
        self.assertIn("src/pkg/parser.py", hint.focus_files)

    def test_evaluate_cli_and_build_hints_cli(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            predictions = root / "predictions.jsonl"
            metrics = root / "metrics.json"
            hints_json = root / "hints.json"
            hints_md = root / "hints.md"
            predictions.write_text(
                json.dumps(
                    {
                        "task_id": "demo__repo-1",
                        "repo": "demo/repo",
                        "valid_json": True,
                        "schema_valid": True,
                        "prediction": {
                            "failure_type": "needs_repair",
                            "focus_files": ["src/pkg/parser.py"],
                            "suggested_queries": ["parse_sequence"],
                            "avoid": ["Avoid broad rewrites."],
                            "next_steps": ["Inspect parser state."],
                        },
                        "reference": {
                            "failure_type": "needs_repair",
                            "focus_files": ["src/pkg/parser.py"],
                            "suggested_queries": [],
                            "avoid": [],
                            "next_steps": [],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with contextlib.redirect_stdout(io.StringIO()):
                eval_code = evaluate_main(
                    [
                        str(predictions),
                        "--output-json",
                        str(metrics),
                        "--focus-k",
                        "1",
                    ]
                )
                hints_code = build_hints_main(
                    [
                        str(predictions),
                        "--output-json",
                        str(hints_json),
                        "--output-md",
                        str(hints_md),
                    ]
                )
            metric_payload = json.loads(metrics.read_text(encoding="utf-8"))
            prompt_hints = load_prompt_hint_map(hints_json)

        self.assertEqual(eval_code, 0)
        self.assertEqual(hints_code, 0)
        self.assertEqual(metric_payload["focus_recall"]["recall@1"], 1.0)
        self.assertIn("demo__repo-1", prompt_hints)
        self.assertIn("Focus files: src/pkg/parser.py", prompt_hints["demo__repo-1"])


if __name__ == "__main__":
    unittest.main()
