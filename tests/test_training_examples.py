import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from repopilot.cli.build_training_dataset import main as training_dataset_main
from repopilot.training.examples import build_training_examples


class TrainingExamplesTest(unittest.TestCase):
    def test_build_examples_creates_critic_and_reranker_labels(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            trajectory_path = _write_trajectory(
                Path(temp_dir) / "trajectory.jsonl",
                _trajectory(final_patch=_patch(), resolved=True),
            )

            examples = build_training_examples([trajectory_path])

        self.assertEqual([example.objective for example in examples], ["critic", "reranker"])
        critic, reranker = examples
        self.assertEqual(critic.target["failure_type"], "resolved")
        self.assertIn("prompt_hint", critic.target)
        self.assertEqual(reranker.target["patch_score_label"], 1)
        self.assertEqual(reranker.changed_files, ["src/pkg/parser.py"])
        self.assertGreater(reranker.patch_lines, 0)
        self.assertIn("Candidate patch", reranker.input_text)

    def test_empty_patch_skips_reranker_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            trajectory_path = _write_trajectory(
                Path(temp_dir) / "trajectory.jsonl",
                _trajectory(final_patch="", resolved=False),
            )

            default_examples = build_training_examples([trajectory_path])
            with_empty_patch = build_training_examples(
                [trajectory_path],
                include_empty_patch_reranker=True,
            )

        self.assertEqual([example.objective for example in default_examples], ["critic"])
        self.assertEqual(
            [example.objective for example in with_empty_patch],
            ["critic", "reranker"],
        )
        self.assertEqual(with_empty_patch[1].target["patch_score_label"], 0)

    def test_training_dataset_cli_writes_jsonl_and_summaries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            trajectory_path = _write_trajectory(
                root / "trajectory.jsonl",
                _trajectory(final_patch=_patch(), resolved=True),
            )
            output_jsonl = root / "examples.jsonl"
            output_json = root / "summary.json"
            output_md = root / "summary.md"

            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                exit_code = training_dataset_main(
                    [
                        str(trajectory_path),
                        "--output-jsonl",
                        str(output_jsonl),
                        "--output-summary-json",
                        str(output_json),
                        "--output-summary-md",
                        str(output_md),
                        "--title",
                        "Training Dataset Test",
                    ]
                )
            rows = [
                json.loads(line)
                for line in output_jsonl.read_text(encoding="utf-8").splitlines()
            ]
            summary = json.loads(output_json.read_text(encoding="utf-8"))
            markdown = output_md.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(rows), 2)
        self.assertEqual(summary["examples"], 2)
        self.assertEqual(summary["critic_examples"], 1)
        self.assertEqual(summary["reranker_examples"], 1)
        self.assertIn("# Training Dataset Test", markdown)
        self.assertIn('"examples": 2', stdout.getvalue())


def _write_trajectory(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return path


def _trajectory(final_patch: str, resolved: bool) -> dict[str, object]:
    return {
        "task_id": "demo__repo-1",
        "repo": "demo/repo",
        "issue": "Parser drops doubled semicolon in `parse_sequence`.",
        "resolved": resolved,
        "final_patch": final_patch,
        "verifier": {
            "resolved": resolved,
            "regression": False,
            "error_summary": "FAILED tests/test_parser.py::test_doubled_semicolon",
        },
        "steps": [
            {
                "action": "verify_baseline",
                "observation": "FAILED tests/test_parser.py::test_doubled_semicolon",
                "metadata": {
                    "error_summary": "FAILED tests/test_parser.py::test_doubled_semicolon",
                    "stderr": "AssertionError: expected unparsable segment",
                },
            },
            {
                "action": "model_action",
                "observation": '{"action": "read_file"}',
                "metadata": {
                    "action": {
                        "action": "read_file",
                        "args": {"path": "src/pkg/parser.py"},
                    }
                },
            },
            {
                "action": "tool:read_file",
                "observation": "1: class Parser: ...",
                "metadata": {
                    "action": {
                        "action": "read_file",
                        "args": {"path": "src/pkg/parser.py"},
                    }
                },
            },
            {
                "action": "model_action_invalid",
                "observation": "I think the fix is in parser.py",
                "metadata": {"error": "invalid JSON"},
            },
            {
                "action": "tool:submit",
                "observation": "resolved=True" if resolved else "still failing",
                "metadata": {
                    "resolved": resolved,
                    "error_summary": "FAILED tests/test_parser.py::test_doubled_semicolon",
                    "stderr": "AssertionError: expected unparsable segment",
                    "test_runs": 2,
                },
            },
        ],
    }


def _patch() -> str:
    return (
        "diff --git a/src/pkg/parser.py b/src/pkg/parser.py\n"
        "--- a/src/pkg/parser.py\n"
        "+++ b/src/pkg/parser.py\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n"
    )


if __name__ == "__main__":
    unittest.main()
