import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from repopilot.cli.report_benchmark import main as report_main
from repopilot.report.benchmark_report import (
    load_benchmark_report,
    render_markdown_report,
)


class BenchmarkReportTest(unittest.TestCase):
    def test_load_report_merges_summary_and_trajectory_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            summary_path, trajectory_path = _write_fixture(root)

            report = load_benchmark_report(summary_path, trajectory_path)

        self.assertEqual(report.total, 2)
        self.assertEqual(report.resolved, 1)
        self.assertEqual(report.timeout_tasks, 1)
        self.assertEqual(report.tasks[0].changed_files, ["pkg/rule.py"])
        self.assertEqual(report.tasks[0].model_steps, 1)
        self.assertEqual(report.tasks[0].tool_steps, 3)
        self.assertEqual(report.tasks[0].test_runs, 3)
        self.assertEqual(report.tasks[1].failure_type, "model_timeout")

    def test_render_markdown_report_contains_summary_and_case_studies(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            summary_path, trajectory_path = _write_fixture(root)
            report = load_benchmark_report(summary_path, trajectory_path)

        markdown = render_markdown_report(report, title="Demo Report")

        self.assertIn("# Demo Report", markdown)
        self.assertIn("| Resolved Rate | 0.500 |", markdown)
        self.assertIn("| `case_success` | yes | 5 |", markdown)
        self.assertIn("### `case_timeout`", markdown)
        self.assertIn("model_timeout", markdown)

    def test_report_cli_writes_markdown_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            summary_path, trajectory_path = _write_fixture(root)
            markdown_path = root / "report.md"
            json_path = root / "report.json"

            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = report_main(
                    [
                        "--summary",
                        str(summary_path),
                        "--trajectory",
                        str(trajectory_path),
                        "--output-md",
                        str(markdown_path),
                        "--output-json",
                        str(json_path),
                        "--title",
                        "CLI Report",
                    ]
                )

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            markdown = markdown_path.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertIn("# CLI Report", markdown)
        self.assertEqual(payload["resolved"], 1)


def _write_fixture(root: Path) -> tuple[Path, Path]:
    summary_path = root / "summary.json"
    trajectory_path = root / "trajectory.jsonl"
    summary_path.write_text(
        json.dumps(
            {
                "total": 2,
                "resolved": 1,
                "resolved_rate": 0.5,
                "tasks": [
                    {
                        "task_id": "case_success",
                        "repo": "demo/repo",
                        "resolved": True,
                        "patch_lines": 5,
                        "workdir": "runs/case_success",
                    },
                    {
                        "task_id": "case_timeout",
                        "repo": "demo/repo",
                        "resolved": False,
                        "patch_lines": 0,
                        "workdir": "runs/case_timeout",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    trajectories = [
        {
            "task_id": "case_success",
            "repo": "demo/repo",
            "issue": "Fix rule output\n\nMore details.",
            "steps": [
                {"action": "verify_baseline", "observation": "failed", "metadata": {}},
                {"action": "model_action", "observation": "read", "metadata": {}},
                {
                    "action": "tool:read_file",
                    "observation": "file",
                    "metadata": {"test_runs": 1},
                },
                {
                    "action": "tool:run_tests",
                    "observation": "passed",
                    "metadata": {"test_runs": 2},
                },
                {
                    "action": "tool:submit",
                    "observation": "done",
                    "metadata": {"test_runs": 3},
                },
            ],
            "final_patch": (
                "diff --git a/pkg/rule.py b/pkg/rule.py\n"
                "--- a/pkg/rule.py\n"
                "+++ b/pkg/rule.py\n"
                "@@ -1 +1 @@\n"
                "-old\n"
                "+new\n"
            ),
            "resolved": True,
        },
        {
            "task_id": "case_timeout",
            "repo": "demo/repo",
            "issue": "Timeout issue",
            "steps": [
                {
                    "action": "model_call_error",
                    "observation": "TimeoutError: request exceeded 60 seconds.",
                    "metadata": {"step": 1},
                }
            ],
            "final_patch": "",
            "resolved": False,
        },
    ]
    trajectory_path.write_text(
        "\n".join(json.dumps(item) for item in trajectories) + "\n",
        encoding="utf-8",
    )
    return summary_path, trajectory_path


if __name__ == "__main__":
    unittest.main()
