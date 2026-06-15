import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from repopilot.cli.compare_benchmark_reports import main as compare_main
from repopilot.report.benchmark_compare import (
    compare_benchmark_reports,
    render_comparison_markdown,
)
from repopilot.report.benchmark_report import load_report_json


class BenchmarkCompareTest(unittest.TestCase):
    def test_compare_reports_counts_task_outcome_transitions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base_path = _write_report_json(
                root / "base.json",
                [
                    _task_payload("case_gain", resolved=False, failure_type="model_timeout"),
                    _task_payload("case_loss", resolved=True, failure_type="resolved"),
                    _task_payload("case_still_ok", resolved=True, failure_type="resolved"),
                    _task_payload("case_still_bad", resolved=False, failure_type="no_patch"),
                ],
            )
            candidate_path = _write_report_json(
                root / "candidate.json",
                [
                    _task_payload("case_gain", resolved=True, failure_type="resolved"),
                    _task_payload("case_loss", resolved=False, failure_type="unresolved_patch"),
                    _task_payload("case_still_ok", resolved=True, failure_type="resolved"),
                    _task_payload(
                        "case_still_bad",
                        resolved=False,
                        failure_type="model_timeout",
                    ),
                ],
            )

            comparison = compare_benchmark_reports(
                load_report_json(base_path),
                load_report_json(candidate_path),
                base_name="base",
                candidate_name="candidate",
                task_order=["case_still_bad", "case_gain", "case_loss", "case_still_ok"],
            )

        self.assertEqual(comparison.base_resolved, 2)
        self.assertEqual(comparison.candidate_resolved, 2)
        self.assertEqual(comparison.delta_resolved, 0)
        self.assertEqual(comparison.gained_tasks, 1)
        self.assertEqual(comparison.lost_tasks, 1)
        self.assertEqual(comparison.still_resolved, 1)
        self.assertEqual(comparison.still_unresolved, 1)
        self.assertEqual(
            [task.task_id for task in comparison.tasks],
            ["case_still_bad", "case_gain", "case_loss", "case_still_ok"],
        )
        self.assertEqual(comparison.tasks[1].status, "gained")
        self.assertEqual(
            comparison.failure_transitions["model_timeout -> resolved"],
            1,
        )

    def test_render_comparison_markdown_contains_delta_and_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base_path = _write_report_json(
                root / "base.json",
                [_task_payload("case_gain", resolved=False, failure_type="no_patch")],
            )
            candidate_path = _write_report_json(
                root / "candidate.json",
                [_task_payload("case_gain", resolved=True, failure_type="resolved")],
            )
            comparison = compare_benchmark_reports(
                load_report_json(base_path),
                load_report_json(candidate_path),
                base_name="initial",
                candidate_name="after_rescue",
            )

        markdown = render_comparison_markdown(comparison, title="Comparison")

        self.assertIn("# Comparison", markdown)
        self.assertIn("| Delta resolved | +1 |", markdown)
        self.assertIn("| `no_patch -> resolved` | 1 |", markdown)
        self.assertIn("| `case_gain` | `gained` |", markdown)

    def test_compare_cli_writes_outputs_and_requires_same_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base_path = _write_report_json(
                root / "base.json",
                [
                    _task_payload("case_a", resolved=False, failure_type="model_timeout"),
                    _task_payload("case_b", resolved=True, failure_type="resolved"),
                ],
            )
            candidate_path = _write_report_json(
                root / "candidate.json",
                [
                    _task_payload("case_a", resolved=True, failure_type="resolved"),
                    _task_payload("case_b", resolved=True, failure_type="resolved"),
                ],
            )
            markdown_path = root / "comparison.md"
            json_path = root / "comparison.json"

            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = compare_main(
                    [
                        "--base",
                        str(base_path),
                        "--candidate",
                        str(candidate_path),
                        "--base-name",
                        "initial",
                        "--candidate-name",
                        "after_rescue",
                        "--require-same-tasks",
                        "--output-md",
                        str(markdown_path),
                        "--output-json",
                        str(json_path),
                        "--title",
                        "CLI Comparison",
                    ]
                )

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            markdown = markdown_path.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["delta_resolved"], 1)
        self.assertEqual(payload["gained_tasks"], 1)
        self.assertIn("# CLI Comparison", markdown)


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
