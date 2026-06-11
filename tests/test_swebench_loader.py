from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
import unittest

from repopilot.benchmark.swebench import load_swebench_jsonl, swebench_record_to_task
from repopilot.sandbox.runner import SandboxRunner
from repopilot.verifier.pytest_verifier import CommandVerifier


class SwebenchLoaderTest(unittest.TestCase):
    def test_convert_swebench_record_to_task(self) -> None:
        record = {
            "instance_id": "demo__repo-1",
            "repo": "demo/repo",
            "base_commit": "abc123",
            "problem_statement": "Fix divide by zero.",
            "hints_text": "Look at calc.py",
            "FAIL_TO_PASS": ["tests/test_calc.py::test_zero"],
            "PASS_TO_PASS": ["tests/test_calc.py::test_regular"],
        }

        task = swebench_record_to_task(record)

        self.assertEqual(task.task_id, "demo__repo-1")
        self.assertEqual(task.repo_url, "https://github.com/demo/repo.git")
        self.assertIn("Hints", task.issue)
        self.assertIn("tests/test_calc.py::test_zero", task.test_command)

    def test_load_jsonl_and_prepare_local_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repo = root / "source_repo"
            repo.mkdir()
            (repo / "calc.py").write_text("def divide(a, b):\n    return a / b\n", encoding="utf-8")
            (repo / "test_calc.py").write_text(
                "import unittest\n\n"
                "from calc import divide\n\n\n"
                "class TestDivide(unittest.TestCase):\n"
                "    def test_regular(self):\n"
                "        self.assertEqual(divide(4, 2), 2)\n\n"
                "    def test_zero(self):\n"
                "        self.assertIsNone(divide(4, 0))\n\n\n"
                "if __name__ == '__main__':\n"
                "    unittest.main()\n",
                encoding="utf-8",
            )
            _git(repo, "init")
            _git(repo, "add", ".")
            _git(repo, "-c", "user.name=RepoPilot", "-c", "user.email=test@example.com", "commit", "-m", "initial")
            base_commit = _git(repo, "rev-parse", "HEAD").strip()

            jsonl = root / "swebench.jsonl"
            test_patch = (
                "diff --git a/test_calc_regression.py b/test_calc_regression.py\n"
                "new file mode 100644\n"
                "--- /dev/null\n"
                "+++ b/test_calc_regression.py\n"
                "@@ -0,0 +1,7 @@\n"
                "+import unittest\n"
                "+from calc import divide\n"
                "+\n"
                "+\n"
                "+class TestRegression(unittest.TestCase):\n"
                "+    def test_zero(self):\n"
                "+        self.assertIsNone(divide(4, 0))\n"
            )
            record = {
                "instance_id": "local__calc-1",
                "repo": "local/calc",
                "local_repo_path": str(repo),
                "base_commit": base_commit,
                "problem_statement": "Return None when dividing by zero.",
                "test_command": "python3 -m unittest discover -s . -p 'test_*regression.py'",
                "test_patch": test_patch,
                "FAIL_TO_PASS": ["test_calc.TestDivide.test_zero"],
                "PASS_TO_PASS": ["test_calc.TestDivide.test_regular"],
            }
            jsonl.write_text(json.dumps(record) + "\n", encoding="utf-8")

            task = load_swebench_jsonl(jsonl)[0]
            runner = SandboxRunner(root=root / "runs")
            workdir = runner.prepare(task)
            result = CommandVerifier(runner).verify(workdir, task.test_command)
            calc_exists = (workdir / "calc.py").exists()
            test_patch_exists = (workdir / "test_calc_regression.py").exists()
            clean_after_prepare = runner.git_diff(workdir) == ""

        self.assertEqual(task.task_id, "local__calc-1")
        self.assertTrue(task.test_patch)
        self.assertTrue(calc_exists)
        self.assertTrue(test_patch_exists)
        self.assertTrue(clean_after_prepare)
        self.assertFalse(result.resolved)


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )
    return completed.stdout


if __name__ == "__main__":
    unittest.main()
