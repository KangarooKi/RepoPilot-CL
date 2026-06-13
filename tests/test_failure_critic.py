import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from repopilot.cli.build_failure_hints import main as hints_main
from repopilot.critic.failure import (
    build_failure_hint,
    load_prompt_hint_map,
    render_failure_hints_markdown,
    render_prompt_hint,
)


class FailureCriticTest(unittest.TestCase):
    def test_build_failure_hint_for_no_patch_trajectory(self) -> None:
        hint = build_failure_hint(_trajectory(final_patch="", resolved=False))

        self.assertEqual(hint.failure_type, "invalid_action_no_patch")
        self.assertIn("src/pkg/parser.py", hint.focus_files)
        self.assertTrue(all("\n" not in query for query in hint.suggested_queries))
        self.assertTrue(any("JSON" in rule for rule in hint.avoid))
        self.assertIn("Previous failure type", render_prompt_hint(hint))

    def test_build_failure_hint_for_unresolved_patch(self) -> None:
        trajectory = _trajectory(
            final_patch=(
                "diff --git a/src/pkg/schema.py b/src/pkg/schema.py\n"
                "--- a/src/pkg/schema.py\n"
                "+++ b/src/pkg/schema.py\n"
                "@@ -1 +1 @@\n"
                "-old\n"
                "+new\n"
            ),
            resolved=False,
        )

        hint = build_failure_hint(trajectory)

        self.assertEqual(hint.failure_type, "unresolved_patch")
        self.assertIn("src/pkg/schema.py", hint.focus_files)
        self.assertTrue(any("previous patch" in rule for rule in hint.avoid))

    def test_render_failure_hints_markdown(self) -> None:
        hint = build_failure_hint(_trajectory(final_patch="", resolved=False))

        markdown = render_failure_hints_markdown([hint], source="trajectory.jsonl")

        self.assertIn("# Failure Critic Hints", markdown)
        self.assertIn("demo__repo-1", markdown)
        self.assertIn("Prompt hint", markdown)

    def test_build_failure_hints_cli_writes_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            trajectory_path = root / "trajectory.jsonl"
            output_json = root / "hints.json"
            output_md = root / "hints.md"
            trajectory_path.write_text(
                json.dumps(_trajectory(final_patch="", resolved=False)) + "\n",
                encoding="utf-8",
            )

            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                exit_code = hints_main(
                    [
                        str(trajectory_path),
                        "--output-json",
                        str(output_json),
                        "--output-md",
                        str(output_md),
                    ]
                )

            payload = json.loads(output_json.read_text(encoding="utf-8"))
            prompt_hints = load_prompt_hint_map(output_json)
            markdown = output_md.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["hints"], 1)
        self.assertEqual(payload["hints"][0]["task_id"], "demo__repo-1")
        self.assertIn("demo__repo-1", markdown)
        self.assertIn("Previous failure type", prompt_hints["demo__repo-1"])


def _trajectory(final_patch: str, resolved: bool) -> dict[str, object]:
    return {
        "task_id": "demo__repo-1",
        "repo": "demo/repo",
        "issue": "Parser drops doubled semicolon in `parse_sequence`.",
        "resolved": resolved,
        "final_patch": final_patch,
        "verifier": {
            "resolved": resolved,
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
                "observation": "still failing",
                "metadata": {
                    "error_summary": "FAILED tests/test_parser.py::test_doubled_semicolon",
                    "stderr": "AssertionError: expected unparsable segment",
                    "test_runs": 2,
                },
            },
        ],
    }


if __name__ == "__main__":
    unittest.main()
