import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from repopilot.cli.merge_benchmark_reports import main as merge_main
from repopilot.cli.report_benchmark import main as report_main
from repopilot.report.benchmark_report import (
    load_report_json,
    load_benchmark_report,
    merge_benchmark_reports,
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
        self.assertEqual(report.failure_types["model_timeout"], 1)
        self.assertEqual(report.failure_types["resolved"], 1)

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
        self.assertIn("## Failure Types", markdown)

    def test_load_report_classifies_prepare_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            summary_path = root / "summary.json"
            trajectory_path = root / "trajectory.jsonl"
            summary_path.write_text(
                json.dumps(
                    {
                        "total": 1,
                        "resolved": 0,
                        "resolved_rate": 0.0,
                        "tasks": [
                            {
                                "task_id": "case_setup",
                                "repo": "demo/repo",
                                "resolved": False,
                                "patch_lines": 0,
                                "workdir": "runs/case_setup",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            trajectory_path.write_text(
                json.dumps(
                    {
                        "task_id": "case_setup",
                        "repo": "demo/repo",
                        "issue": "Install fails",
                        "steps": [
                            {
                                "action": "prepare_error",
                                "observation": "RuntimeError: Setup command failed for case_setup: pip timed out",
                                "metadata": {"error_type": "RuntimeError"},
                            }
                        ],
                        "final_patch": "",
                        "resolved": False,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            report = load_benchmark_report(summary_path, trajectory_path)

        self.assertEqual(report.tasks[0].failure_type, "setup_error")
        self.assertEqual(report.failure_types, {"setup_error": 1})

    def test_load_report_classifies_invalid_test_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            summary_path = root / "summary.json"
            trajectory_path = root / "trajectory.jsonl"
            summary_path.write_text(
                json.dumps(
                    {
                        "total": 1,
                        "resolved": 0,
                        "resolved_rate": 0.0,
                        "tasks": [
                            {
                                "task_id": "case_bad_test",
                                "repo": "demo/repo",
                                "resolved": False,
                                "patch_lines": 0,
                                "workdir": "runs/case_bad_test",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            trajectory_path.write_text(
                json.dumps(
                    {
                        "task_id": "case_bad_test",
                        "repo": "demo/repo",
                        "issue": "Bad test selector",
                        "steps": [
                            {
                                "action": "prepare",
                                "observation": "Created sandbox",
                                "metadata": {},
                            },
                            {
                                "action": "verify_baseline",
                                "observation": "ERROR: file or directory not found: bad_selector",
                                "metadata": {
                                    "error_summary": "ERROR: file or directory not found: bad_selector"
                                },
                            },
                        ],
                        "verifier": {
                            "error_summary": "ERROR: file or directory not found: bad_selector"
                        },
                        "final_patch": "",
                        "resolved": False,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            report = load_benchmark_report(summary_path, trajectory_path)

        self.assertEqual(report.tasks[0].failure_type, "test_command_error")
        self.assertEqual(report.failure_types, {"test_command_error": 1})

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

    def test_merge_reports_prefers_resolved_and_keeps_task_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base_path = _write_report_json(
                root / "base.json",
                [
                    _task_payload("case_a", resolved=False, failure_type="model_timeout"),
                    _task_payload("case_b", resolved=True, failure_type="resolved"),
                    _task_payload("case_c", resolved=False, failure_type="no_patch"),
                ],
            )
            rescue_path = _write_report_json(
                root / "rescue.json",
                [
                    _task_payload("case_a", resolved=True, failure_type="resolved"),
                    _task_payload("case_c", resolved=False, failure_type="unresolved_patch"),
                ],
            )

            merged = merge_benchmark_reports(
                [load_report_json(base_path), load_report_json(rescue_path)],
                task_order=["case_c", "case_b", "case_a"],
            )

        self.assertEqual(merged.total, 3)
        self.assertEqual(merged.resolved, 2)
        self.assertEqual([task.task_id for task in merged.tasks], ["case_c", "case_b", "case_a"])
        self.assertEqual(merged.tasks[0].failure_type, "unresolved_patch")
        self.assertTrue(merged.tasks[2].resolved)

    def test_merge_report_cli_writes_outputs_and_checks_task_count(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base_path = _write_report_json(
                root / "base.json",
                [
                    _task_payload("case_a", resolved=False, failure_type="model_timeout"),
                    _task_payload("case_b", resolved=True, failure_type="resolved"),
                ],
            )
            rescue_path = _write_report_json(
                root / "rescue.json",
                [_task_payload("case_a", resolved=True, failure_type="resolved")],
            )
            task_ids_path = root / "task_ids.txt"
            task_ids_path.write_text("case_b\ncase_a\n", encoding="utf-8")
            markdown_path = root / "merged.md"
            json_path = root / "merged.json"

            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = merge_main(
                    [
                        str(base_path),
                        str(rescue_path),
                        "--task-ids-file",
                        str(task_ids_path),
                        "--require-task-count",
                        "2",
                        "--output-md",
                        str(markdown_path),
                        "--output-json",
                        str(json_path),
                        "--title",
                        "Merged Report",
                    ]
                )

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            markdown = markdown_path.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["resolved"], 2)
        self.assertEqual([task["task_id"] for task in payload["tasks"]], ["case_b", "case_a"])
        self.assertIn("# Merged Report", markdown)


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


def _write_report_json(path: Path, tasks: list[dict[str, object]]) -> Path:
    resolved = sum(1 for task in tasks if task["resolved"])
    payload = {
        "total": len(tasks),
        "resolved": resolved,
        "resolved_rate": resolved / len(tasks) if tasks else 0.0,
        "tasks": tasks,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _task_payload(
    task_id: str,
    *,
    resolved: bool,
    failure_type: str,
) -> dict[str, object]:
    return {
        "task_id": task_id,
        "repo": "demo/repo",
        "resolved": resolved,
        "patch_lines": 5 if resolved else 0,
        "model_steps": 2,
        "tool_steps": 2,
        "test_runs": 1,
        "changed_files": ["pkg/rule.py"] if resolved else [],
        "failure_type": failure_type,
        "model_errors": 0,
        "invalid_actions": 0,
        "issue_title": f"Issue for {task_id}",
        "patch_preview": "",
    }


if __name__ == "__main__":
    unittest.main()
