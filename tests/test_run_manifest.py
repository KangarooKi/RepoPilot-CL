import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from repopilot.cli.write_run_manifest import main as manifest_main
from repopilot.report.run_manifest import (
    build_run_manifest,
    render_run_manifest_markdown,
)


class RunManifestTest(unittest.TestCase):
    def test_build_manifest_hashes_artifacts_and_reads_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = _write_file(root / "tasks.jsonl", b'{"task_id":"case_a"}\n')
            task_ids = _write_file(root / "task_ids.txt", b"case_a\n")
            report = _write_report_json(root / "report.json")
            config = _write_file(root / "config.json", b'{"env":"test"}\n')

            manifest = build_run_manifest(
                name="demo",
                command="python3 -m repopilot.cli.run_benchmark tasks.jsonl",
                dataset=str(dataset),
                task_ids_file=str(task_ids),
                provider="deepseek-tools",
                model="deepseek-v4-flash",
                report_json=str(report),
                git_commit="abc123",
                artifacts=[("config", str(config))],
                notes=["deterministic test"],
                created_at_utc="2026-06-15T00:00:00+00:00",
            )

        self.assertEqual(manifest.metrics["total"], 2)
        self.assertEqual(manifest.metrics["resolved"], 1)
        self.assertEqual(manifest.metrics["failure_types"], {"resolved": 1, "no_patch": 1})
        self.assertEqual(manifest.git_commit, "abc123")
        self.assertEqual(manifest.artifacts[0].label, "dataset")
        self.assertEqual(
            manifest.artifacts[0].sha256,
            hashlib.sha256(b'{"task_id":"case_a"}\n').hexdigest(),
        )

    def test_render_manifest_markdown_contains_command_and_hash_table(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = _write_file(root / "tasks.jsonl", b"{}\n")
            task_ids = _write_file(root / "task_ids.txt", b"case_a\n")
            report = _write_report_json(root / "report.json")
            manifest = build_run_manifest(
                name="demo",
                command="python3 -m repopilot.cli.run_benchmark tasks.jsonl",
                dataset=str(dataset),
                task_ids_file=str(task_ids),
                provider="scripted",
                model="none",
                report_json=str(report),
                git_commit="abc123",
                artifacts=[],
                created_at_utc="2026-06-15T00:00:00+00:00",
            )

        markdown = render_run_manifest_markdown(manifest)

        self.assertIn("# Run Manifest: demo", markdown)
        self.assertIn("```bash\npython3 -m repopilot.cli.run_benchmark tasks.jsonl\n```", markdown)
        self.assertIn("| `dataset` |", markdown)
        self.assertIn("| resolved | 1 |", markdown)

    def test_manifest_cli_writes_markdown_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = _write_file(root / "tasks.jsonl", b"{}\n")
            task_ids = _write_file(root / "task_ids.txt", b"case_a\n")
            report = _write_report_json(root / "report.json")
            markdown_path = root / "manifest.md"
            json_path = root / "manifest.json"

            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = manifest_main(
                    [
                        "--name",
                        "CLI Manifest",
                        "--command",
                        "python3 -m repopilot.cli.run_benchmark tasks.jsonl",
                        "--dataset",
                        str(dataset),
                        "--task-ids-file",
                        str(task_ids),
                        "--provider",
                        "deepseek-tools",
                        "--model",
                        "deepseek-v4-flash",
                        "--report-json",
                        str(report),
                        "--git-commit",
                        "abc123",
                        "--created-at",
                        "2026-06-15T00:00:00+00:00",
                        "--note",
                        "test note",
                        "--output-md",
                        str(markdown_path),
                        "--output-json",
                        str(json_path),
                    ]
                )

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            markdown = markdown_path.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["name"], "CLI Manifest")
        self.assertEqual(payload["metrics"]["resolved"], 1)
        self.assertIn("test note", markdown)


def _write_report_json(path: Path) -> Path:
    payload = {
        "total": 2,
        "resolved": 1,
        "resolved_rate": 0.5,
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


def _write_file(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


if __name__ == "__main__":
    unittest.main()
