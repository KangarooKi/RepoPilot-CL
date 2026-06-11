from pathlib import Path
import subprocess
import tempfile
import unittest

from repopilot.benchmark.task_loader import Task
from repopilot.benchmark.task_loader import load_task
from repopilot.sandbox.runner import SandboxRunner
from repopilot.verifier.pytest_verifier import CommandVerifier


class SandboxVerifierTest(unittest.TestCase):
    def test_toy_task_fails_before_patch(self) -> None:
        task = load_task(Path("tasks/toy/divide_by_zero/task.json"))
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = SandboxRunner(root=temp_dir)
            workdir = runner.prepare(task)
            result = CommandVerifier(runner).verify(workdir, task.test_command)

        self.assertFalse(result.resolved)
        self.assertNotEqual(result.returncode, 0)

    def test_apply_patch_normalizes_missing_trailing_newline(self) -> None:
        task = load_task(Path("tasks/toy/string_normalization/task.json"))
        diff = (
            "--- a/names.py\n"
            "+++ b/names.py\n"
            "@@ -1,2 +1,2 @@\n"
            " def normalize_name(name):\n"
            "-    return name.lower()\n"
            "+    return name.strip().lower()"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = SandboxRunner(root=temp_dir)
            workdir = runner.prepare(task)
            apply_result = runner.apply_unified_diff(workdir, diff)
            content = runner.read_file(workdir, "names.py")

        self.assertEqual(apply_result.returncode, 0)
        self.assertIn("strip().lower()", content)

    def test_prepare_remote_repo_uses_cache_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            source.mkdir()
            (source / "hello.py").write_text("VALUE = 1\n", encoding="utf-8")
            _git(source, "init")
            _git(source, "add", ".")
            _git(
                source,
                "-c",
                "user.name=RepoPilot",
                "-c",
                "user.email=test@example.com",
                "commit",
                "-m",
                "initial",
            )
            base_commit = _git(source, "rev-parse", "HEAD").strip()
            task = Task(
                task_id="cached_repo_task",
                repo="local/cache-demo",
                repo_url=str(source),
                base_commit=base_commit,
                issue="Inspect cached clone.",
                test_command="python3 -c 'import hello; assert hello.VALUE == 1'",
            )

            runner = SandboxRunner(root=root / "runs", repo_cache_dir=root / "cache")
            workdir = runner.prepare(task)
            result = runner.run_command(workdir, task.test_command)

            self.assertEqual(result.returncode, 0)
            self.assertTrue((root / "cache" / "local__cache-demo").exists())
            self.assertTrue((workdir / "hello.py").exists())


if __name__ == "__main__":
    unittest.main()


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )
    return completed.stdout
