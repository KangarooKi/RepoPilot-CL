import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from repopilot.cli.summarize_benchmark_suite import main as suite_main
from repopilot.report.benchmark_report import load_report_json
from repopilot.report.benchmark_suite import (
    NamedBenchmarkReport,
    build_benchmark_suite,
    render_suite_markdown,
)


class BenchmarkSuiteTest(unittest.TestCase):
    def test_build_suite_report_tracks_baseline_deltas_and_repos(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base_path = _write_report_json(
                root / "base.json",
                [
                    _task_payload(
                        "case_a",
                        repo="demo/repo1",
                        resolved=False,
                        failure_type="model_timeout",
                    ),
                    _task_payload(
                        "case_b",
                        repo="demo/repo1",
                        resolved=True,
                        failure_type="resolved",
                    ),
                    _task_payload(
                        "case_c",
                        repo="demo/repo2",
                        resolved=False,
                        failure_type="no_patch",
                    ),
                ],
            )
            candidate_path = _write_report_json(
                root / "candidate.json",
                [
                    _task_payload(
                        "case_a",
                        repo="demo/repo1",
                        resolved=True,
                        failure_type="resolved",
                    ),
                    _task_payload(
                        "case_b",
                        repo="demo/repo1",
                        resolved=True,
                        failure_type="resolved",
                    ),
                    _task_payload(
                        "case_c",
                        repo="demo/repo2",
                        resolved=False,
                        failure_type="unresolved_patch",
                    ),
                ],
            )

            suite = build_benchmark_suite(
                [
                    NamedBenchmarkReport(
                        "base",
                        str(base_path),
                        load_report_json(base_path),
                    ),
                    NamedBenchmarkReport(
                        "candidate",
                        str(candidate_path),
                        load_report_json(candidate_path),
                    ),
                ],
                baseline_name="base",
                require_same_tasks=True,
            )

        self.assertEqual(suite.baseline, "base")
        self.assertEqual(suite.entries[0].delta_resolved, 0)
        self.assertEqual(suite.entries[1].delta_resolved, 1)
        self.assertEqual(suite.entries[1].gained_tasks, 1)
        self.assertEqual(suite.entries[1].lost_tasks, 0)
        self.assertEqual(suite.entries[1].still_unresolved, 1)
        self.assertEqual(suite.entries[1].repo_breakdown[0].repo, "demo/repo1")
        self.assertEqual(suite.entries[1].repo_breakdown[0].resolved, 2)

    def test_render_suite_markdown_contains_variant_and_repo_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base_path = _write_report_json(
                root / "base.json",
                [_task_payload("case_a", repo="demo/repo", resolved=False)],
            )
            candidate_path = _write_report_json(
                root / "candidate.json",
                [_task_payload("case_a", repo="demo/repo", resolved=True)],
            )
            suite = build_benchmark_suite(
                [
                    NamedBenchmarkReport("base", str(base_path), load_report_json(base_path)),
                    NamedBenchmarkReport(
                        "candidate",
                        str(candidate_path),
                        load_report_json(candidate_path),
                    ),
                ]
            )

        markdown = render_suite_markdown(suite)

        self.assertIn("# RepoPilot-CL Benchmark Suite", markdown)
        self.assertIn("| `candidate` | 1 | 1 | 1.000 | +1 | 1 | 0 | 0 |", markdown)
        self.assertIn("## Repository Breakdown", markdown)

    def test_suite_cli_writes_markdown_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base_path = _write_report_json(
                root / "base.json",
                [_task_payload("case_a", repo="demo/repo", resolved=False)],
            )
            candidate_path = _write_report_json(
                root / "candidate.json",
                [_task_payload("case_a", repo="demo/repo", resolved=True)],
            )
            markdown_path = root / "suite.md"
            json_path = root / "suite.json"

            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = suite_main(
                    [
                        "--report",
                        f"base={base_path}",
                        "--report",
                        f"candidate={candidate_path}",
                        "--baseline",
                        "base",
                        "--require-same-tasks",
                        "--output-md",
                        str(markdown_path),
                        "--output-json",
                        str(json_path),
                        "--title",
                        "CLI Suite",
                    ]
                )

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            markdown = markdown_path.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["baseline"], "base")
        self.assertEqual(payload["entries"][1]["delta_resolved"], 1)
        self.assertIn("# CLI Suite", markdown)


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
    repo: str,
    resolved: bool,
    failure_type: str | None = None,
) -> dict[str, object]:
    return {
        "task_id": task_id,
        "repo": repo,
        "resolved": resolved,
        "patch_lines": 5 if resolved else 0,
        "model_steps": 2,
        "tool_steps": 2,
        "test_runs": 1,
        "changed_files": ["pkg/rule.py"] if resolved else [],
        "failure_type": failure_type or ("resolved" if resolved else "no_patch"),
        "model_errors": 0,
        "invalid_actions": 0,
        "issue_title": f"Issue for {task_id}",
        "patch_preview": "",
    }


if __name__ == "__main__":
    unittest.main()
