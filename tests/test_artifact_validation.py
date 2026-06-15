import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from repopilot.cli.validate_benchmark_artifacts import main as validate_main
from repopilot.report.artifact_validation import (
    validate_artifacts,
    validate_benchmark_report,
    validate_run_manifest,
)
from repopilot.report.run_manifest import build_run_manifest, write_run_manifest_artifacts


class ArtifactValidationTest(unittest.TestCase):
    def test_validate_benchmark_report_accepts_consistent_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = _write_report_json(Path(temp_dir) / "report.json")

            checks = validate_benchmark_report(report_path)

        self.assertTrue(all(check.passed for check in checks))

    def test_validate_benchmark_report_flags_metric_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = _write_report_json(Path(temp_dir) / "report.json")
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            payload["resolved"] = 2
            report_path.write_text(json.dumps(payload), encoding="utf-8")

            checks = validate_benchmark_report(report_path)

        failed = [check.check for check in checks if not check.passed]
        self.assertIn("resolved_matches_tasks", failed)

    def test_validate_manifest_recomputes_artifact_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = _write_file(root / "tasks.jsonl", b"{}\n")
            task_ids = _write_file(root / "task_ids.txt", b"case_a\ncase_b\n")
            report_path = _write_report_json(root / "report.json")
            manifest = build_run_manifest(
                name="demo",
                command="python3 -m repopilot.cli.run_benchmark tasks.jsonl",
                dataset=str(dataset),
                task_ids_file=str(task_ids),
                provider="scripted",
                model="none",
                report_json=str(report_path),
                git_commit="abc123",
                artifacts=[],
                created_at_utc="2026-06-15T00:00:00+00:00",
            )
            manifest_path = root / "manifest.json"
            write_run_manifest_artifacts(manifest, root / "manifest.md", manifest_path)
            dataset.write_text("changed\n", encoding="utf-8")

            checks = validate_run_manifest(manifest_path)

        failed = [check.check for check in checks if not check.passed]
        self.assertIn("dataset:size_matches", failed)
        self.assertIn("dataset:sha256_matches", failed)

    def test_validation_cli_writes_outputs_and_returns_failure_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = _write_report_json(root / "report.json")
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            payload["total"] = 99
            report_path.write_text(json.dumps(payload), encoding="utf-8")
            markdown_path = root / "validation.md"
            json_path = root / "validation.json"

            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = validate_main(
                    [
                        "--report",
                        str(report_path),
                        "--output-md",
                        str(markdown_path),
                        "--output-json",
                        str(json_path),
                    ]
                )

            validation = json.loads(json_path.read_text(encoding="utf-8"))
            markdown_exists = markdown_path.exists()

        self.assertEqual(exit_code, 1)
        self.assertFalse(validation["passed"])
        self.assertTrue(markdown_exists)

    def test_validate_artifacts_combines_multiple_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = _write_report_json(root / "report.json")
            comparison_path = _write_comparison_json(root / "comparison.json")
            suite_path = _write_suite_json(root / "suite.json")

            report = validate_artifacts(
                reports=[str(report_path)],
                comparisons=[str(comparison_path)],
                suites=[str(suite_path)],
            )

        self.assertTrue(report.passed)
        self.assertGreater(report.total_checks, 1)


def _write_report_json(path: Path) -> Path:
    payload = {
        "total": 2,
        "resolved": 1,
        "resolved_rate": 0.5,
        "failure_types": {"resolved": 1, "no_patch": 1},
        "tasks": [
            {
                "task_id": "case_a",
                "repo": "demo/repo",
                "resolved": True,
                "patch_lines": 5,
                "model_steps": 2,
                "tool_steps": 2,
                "test_runs": 1,
                "changed_files": ["pkg/rule.py"],
                "failure_type": "resolved",
                "model_errors": 0,
                "invalid_actions": 0,
                "issue_title": "Issue A",
                "patch_preview": "",
            },
            {
                "task_id": "case_b",
                "repo": "demo/repo",
                "resolved": False,
                "patch_lines": 0,
                "model_steps": 1,
                "tool_steps": 1,
                "test_runs": 1,
                "changed_files": [],
                "failure_type": "no_patch",
                "model_errors": 0,
                "invalid_actions": 0,
                "issue_title": "Issue B",
                "patch_preview": "",
            },
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_comparison_json(path: Path) -> Path:
    payload = {
        "base_name": "base",
        "candidate_name": "candidate",
        "base_total": 2,
        "candidate_total": 2,
        "common_tasks": 2,
        "base_resolved": 1,
        "candidate_resolved": 2,
        "delta_resolved": 1,
        "gained_tasks": 1,
        "lost_tasks": 0,
        "still_resolved": 1,
        "still_unresolved": 0,
        "base_only_tasks": 0,
        "candidate_only_tasks": 0,
        "failure_transitions": {"no_patch -> resolved": 1, "resolved -> resolved": 1},
        "tasks": [
            {
                "task_id": "case_a",
                "repo": "demo/repo",
                "status": "still_resolved",
                "base_resolved": True,
                "candidate_resolved": True,
                "base_failure_type": "resolved",
                "candidate_failure_type": "resolved",
                "issue_title": "Issue A",
            },
            {
                "task_id": "case_b",
                "repo": "demo/repo",
                "status": "gained",
                "base_resolved": False,
                "candidate_resolved": True,
                "base_failure_type": "no_patch",
                "candidate_failure_type": "resolved",
                "issue_title": "Issue B",
            },
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_suite_json(path: Path) -> Path:
    payload = {
        "title": "suite",
        "baseline": "base",
        "entries": [
            {
                "name": "base",
                "path": "base.json",
                "total": 2,
                "resolved": 1,
                "resolved_rate": 0.5,
                "delta_resolved": 0,
                "gained_tasks": 0,
                "lost_tasks": 0,
                "still_unresolved": 1,
                "failure_types": {"resolved": 1, "no_patch": 1},
                "repo_breakdown": [
                    {
                        "variant": "base",
                        "repo": "demo/repo",
                        "total": 2,
                        "resolved": 1,
                        "resolved_rate": 0.5,
                    }
                ],
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_file(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


if __name__ == "__main__":
    unittest.main()
