import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from repopilot.benchmark.rescue import load_rescue_cases, render_rescue_markdown
from repopilot.cli.plan_rescue import main as rescue_main


class RescuePlanTest(unittest.TestCase):
    def test_load_rescue_cases_reads_unresolved_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = _write_report(Path(temp_dir))

            cases = load_rescue_cases(report_path)

        self.assertEqual([case.task_id for case in cases], ["case_no_patch", "case_timeout"])
        self.assertEqual(cases[0].failure_type, "no_patch")

    def test_load_rescue_cases_filters_failure_types(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = _write_report(Path(temp_dir))

            cases = load_rescue_cases(report_path, failure_types={"model_timeout"})

        self.assertEqual([case.task_id for case in cases], ["case_timeout"])

    def test_render_rescue_markdown_contains_failure_mix_and_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = _write_report(Path(temp_dir))
            cases = load_rescue_cases(report_path)

        markdown = render_rescue_markdown(
            cases,
            source_report="report.json",
            task_ids_path="ids.txt",
            recommended_command="python3 -m repopilot.cli.run_benchmark ...",
        )

        self.assertIn("| `model_timeout` | 1 |", markdown)
        self.assertIn("case_no_patch", markdown)
        self.assertIn("Recommended Rerun", markdown)

    def test_rescue_cli_writes_task_ids_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = _write_report(root)
            ids_path = root / "ids.txt"
            markdown_path = root / "rescue.md"

            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                exit_code = rescue_main(
                    [
                        "--report",
                        str(report_path),
                        "--output-task-ids",
                        str(ids_path),
                        "--output-md",
                        str(markdown_path),
                    ]
                )

            payload = json.loads(stdout.getvalue())
            task_ids = ids_path.read_text(encoding="utf-8").splitlines()
            markdown = markdown_path.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertEqual(task_ids, ["case_no_patch", "case_timeout"])
        self.assertIn("case_timeout", markdown)
        self.assertEqual(payload["task_ids"], ["case_no_patch", "case_timeout"])


def _write_report(root: Path) -> Path:
    path = root / "report.json"
    path.write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "task_id": "case_resolved",
                        "repo": "demo/repo",
                        "resolved": True,
                        "failure_type": "resolved",
                    },
                    {
                        "task_id": "case_no_patch",
                        "repo": "demo/repo",
                        "resolved": False,
                        "failure_type": "no_patch",
                        "issue_title": "No patch issue",
                        "changed_files": [],
                    },
                    {
                        "task_id": "case_timeout",
                        "repo": "demo/repo",
                        "resolved": False,
                        "failure_type": "model_timeout",
                        "issue_title": "Timeout issue",
                        "changed_files": [],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    return path


if __name__ == "__main__":
    unittest.main()
