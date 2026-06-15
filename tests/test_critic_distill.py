import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from repopilot.cli.build_critic_sft_dataset import main as critic_sft_main
from repopilot.critic.distill import (
    split_critic_sft_by_task,
    swebench_record_to_critic_sft,
    training_example_to_critic_sft,
)


class CriticDistillTest(unittest.TestCase):
    def test_swebench_record_to_critic_sft_uses_gold_patch_as_target_only(self) -> None:
        example = swebench_record_to_critic_sft(_swebench_record(), source="tasks.jsonl")

        assistant = json.loads(example.messages[-1]["content"])

        self.assertEqual(example.source_kind, "swebench_gold")
        self.assertEqual(example.task_id, "demo__repo-1")
        self.assertIn("src/pkg/parser.py", assistant["focus_files"])
        self.assertEqual(assistant["failure_type"], "needs_repair")
        self.assertIn("Parser drops doubled semicolon", example.messages[1]["content"])
        self.assertNotIn("diff --git", example.messages[1]["content"])

    def test_training_example_to_critic_sft_strips_prompt_hint_from_target(self) -> None:
        example = training_example_to_critic_sft(
            {
                "objective": "critic",
                "task_id": "demo__repo-1",
                "repo": "demo/repo",
                "input_text": "Repository: demo/repo\nIssue: parser fails",
                "target": {
                    "failure_type": "unresolved_patch",
                    "focus_files": ["src/pkg/parser.py"],
                    "suggested_queries": ["parse_sequence"],
                    "avoid": ["Avoid broad rewrites."],
                    "next_steps": ["Inspect parser state."],
                    "prompt_hint": "human-readable hint",
                },
                "resolved": False,
            }
        )

        self.assertIsNotNone(example)
        assert example is not None
        assistant = json.loads(example.messages[-1]["content"])
        self.assertEqual(example.source_kind, "repopilot_trajectory")
        self.assertNotIn("prompt_hint", assistant)
        self.assertEqual(assistant["failure_type"], "unresolved_patch")

    def test_resolved_training_example_exports_success_pattern(self) -> None:
        payload = _training_example("demo__repo-resolved")
        payload["resolved"] = True
        target = payload["target"]
        assert isinstance(target, dict)
        target["failure_type"] = "resolved"
        target["next_steps"] = ["Patch the behavior that still fails the target test."]

        example = training_example_to_critic_sft(payload)

        self.assertIsNotNone(example)
        assert example is not None
        assistant = json.loads(example.messages[-1]["content"])
        self.assertEqual(assistant["failure_type"], "resolved")
        self.assertIn("successful localization pattern", assistant["next_steps"][0])
        self.assertNotIn("still fails", " ".join(assistant["next_steps"]))

    def test_training_example_sanitizes_local_workspace_paths(self) -> None:
        payload = _training_example("demo__repo-path")
        payload["input_text"] = (
            "Final signal: /Users/leiboqi/Documents/Codex/RepoPilot-CL/runs/case "
            "and /private/tmp/demo-path"
        )
        target = payload["target"]
        assert isinstance(target, dict)
        target["focus_files"] = [
            "src/pkg/parser.py",
            "Users/leiboqi/Documents/Codex/RepoPilot-CL/runs/case/src/pkg/parser.py",
        ]

        example = training_example_to_critic_sft(payload)

        self.assertIsNotNone(example)
        assert example is not None
        self.assertIn("<repopilot-workspace>/runs/case", example.input_text)
        self.assertIn("<tmp-path>", example.input_text)
        self.assertNotIn("/Users/", example.input_text)
        assistant = json.loads(example.messages[-1]["content"])
        self.assertEqual(assistant["focus_files"], ["src/pkg/parser.py"])

    def test_split_is_task_level(self) -> None:
        examples = [
            swebench_record_to_critic_sft(
                {**_swebench_record(), "instance_id": f"demo__repo-{idx}"},
                source="tasks.jsonl",
            )
            for idx in range(10)
        ]

        splits = split_critic_sft_by_task(examples, train_ratio=0.6, dev_ratio=0.2, seed=7)
        task_to_split = {}
        for split, rows in splits.items():
            for row in rows:
                previous = task_to_split.setdefault(row.task_id, split)
                self.assertEqual(previous, split)

        self.assertEqual(len(task_to_split), 10)
        self.assertGreater(len(splits["train"]), 0)
        self.assertGreater(len(splits["dev"]), 0)
        self.assertGreater(len(splits["test"]), 0)

    def test_cli_writes_sft_dataset_summary_and_splits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            swebench_path = root / "tasks.jsonl"
            examples_path = root / "training_examples.jsonl"
            output_path = root / "critic_sft.jsonl"
            split_dir = root / "splits"
            summary_json = root / "summary.json"
            summary_md = root / "summary.md"
            swebench_path.write_text(
                "\n".join(
                    json.dumps({**_swebench_record(), "instance_id": f"demo__repo-{idx}"})
                    for idx in range(4)
                )
                + "\n",
                encoding="utf-8",
            )
            examples_path.write_text(
                json.dumps(_training_example("demo__repo-own")) + "\n",
                encoding="utf-8",
            )

            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                exit_code = critic_sft_main(
                    [
                        "--swebench-jsonl",
                        str(swebench_path),
                        "--training-examples-jsonl",
                        str(examples_path),
                        "--output-jsonl",
                        str(output_path),
                        "--split-output-dir",
                        str(split_dir),
                        "--output-summary-json",
                        str(summary_json),
                        "--output-summary-md",
                        str(summary_md),
                    ]
                )
            rows = [
                json.loads(line)
                for line in output_path.read_text(encoding="utf-8").splitlines()
            ]
            summary = json.loads(summary_json.read_text(encoding="utf-8"))
            split_exists = (split_dir / "critic_train.jsonl").exists()

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(rows), 5)
        self.assertEqual(summary["examples"], 5)
        self.assertEqual(summary["source_kinds"]["swebench_gold"], 4)
        self.assertEqual(summary["source_kinds"]["repopilot_trajectory"], 1)
        self.assertTrue(split_exists)
        self.assertIn('"examples": 5', stdout.getvalue())


def _swebench_record() -> dict[str, object]:
    return {
        "repo": "demo/repo",
        "instance_id": "demo__repo-1",
        "problem_statement": "Parser drops doubled semicolon in parse_sequence.",
        "patch": (
            "diff --git a/src/pkg/parser.py b/src/pkg/parser.py\n"
            "--- a/src/pkg/parser.py\n"
            "+++ b/src/pkg/parser.py\n"
            "@@ -1 +1 @@\n"
            "-old\n"
            "+new\n"
        ),
        "FAIL_TO_PASS": json.dumps(["tests/test_parser.py::test_doubled_semicolon"]),
        "PASS_TO_PASS": json.dumps(["tests/test_parser.py::test_existing_parse"]),
        "created_at": "2026-01-01T00:00:00Z",
        "version": "1.0",
    }


def _training_example(task_id: str) -> dict[str, object]:
    return {
        "objective": "critic",
        "task_id": task_id,
        "repo": "demo/repo",
        "input_text": "Repository: demo/repo\nIssue: parser fails",
        "target": {
            "failure_type": "unresolved_patch",
            "focus_files": ["src/pkg/parser.py"],
            "suggested_queries": ["parse_sequence"],
            "avoid": ["Avoid broad rewrites."],
            "next_steps": ["Inspect parser state."],
        },
        "resolved": False,
        "model_steps": 2,
        "tool_steps": 3,
        "test_runs": 1,
    }


if __name__ == "__main__":
    unittest.main()
