import os
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

    def test_apply_patch_recounts_malformed_hunk_lengths(self) -> None:
        task = load_task(Path("tasks/toy/string_normalization/task.json"))
        diff = (
            "--- a/names.py\n"
            "+++ b/names.py\n"
            "@@ -1,1 +1,99 @@\n"
            " def normalize_name(name):\n"
            "-    return name.lower()\n"
            "+    return name.strip().lower()\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = SandboxRunner(root=temp_dir)
            workdir = runner.prepare(task)
            apply_result = runner.apply_unified_diff(workdir, diff)
            content = runner.read_file(workdir, "names.py")

        self.assertEqual(apply_result.returncode, 0, apply_result.stderr)
        self.assertIn("strip().lower()", content)

    def test_apply_patch_repairs_unique_std_prefixed_path(self) -> None:
        task = Task(
            task_id="path_repair",
            repo="toy/path-repair",
            issue="Repair a rule file.",
            test_command="python3 -c 'pass'",
            initial_files={"src/rules/L060.py": "MESSAGE = 'old'\n"},
        )
        diff = (
            "--- a/src/rules/std_L060.py\n"
            "+++ b/src/rules/std_L060.py\n"
            "@@ -1 +1 @@\n"
            "-MESSAGE = 'old'\n"
            "+MESSAGE = 'new'\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = SandboxRunner(root=temp_dir)
            workdir = runner.prepare(task)
            apply_result = runner.apply_unified_diff(workdir, diff)
            content = runner.read_file(workdir, "src/rules/L060.py")

        self.assertEqual(apply_result.returncode, 0, apply_result.stderr)
        self.assertIn("MESSAGE = 'new'", content)

    def test_replace_text_requires_unique_match(self) -> None:
        task = Task(
            task_id="ambiguous_replace",
            repo="toy/replace",
            issue="Replace one target only.",
            test_command="python3 -m pytest",
            initial_files={"module.py": "VALUE = 1\nVALUE = 1\n"},
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = SandboxRunner(root=temp_dir)
            workdir = runner.prepare(task)
            result = runner.replace_text(workdir, "module.py", "VALUE = 1\n", "VALUE = 2\n")
            content = runner.read_file(workdir, "module.py")

        self.assertEqual(result.returncode, 1)
        self.assertIn("Expected exactly one match", result.stderr)
        self.assertEqual(content, "VALUE = 1\nVALUE = 1\n")

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

    def test_prepare_with_venv_runs_setup_and_tests_in_venv(self) -> None:
        task = Task(
            task_id="venv_task",
            repo="toy/venv",
            issue="Verify commands run inside venv.",
            initial_files={"module.py": "VALUE = 1\n"},
            setup_command=(
                "python -c \"import sys, pathlib; "
                "pathlib.Path('setup_prefix.txt').write_text(sys.prefix)\""
            ),
            test_command=(
                "python -c \"import sys, pathlib; "
                "assert pathlib.Path(sys.prefix).name == 'venv_task'; "
                "assert pathlib.Path('setup_prefix.txt').read_text() == sys.prefix\""
            ),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner = SandboxRunner(root=root / "runs", use_venv=True)
            workdir = runner.prepare(task)
            result = runner.run_command(workdir, task.test_command)

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_prepare_with_relative_root_uses_created_venv(self) -> None:
        task = Task(
            task_id="relative_venv_task",
            repo="toy/venv",
            issue="Verify relative runner roots point PATH to the created venv.",
            initial_files={"module.py": "VALUE = 1\n"},
            test_command=(
                "python -c \"import sys, pathlib; "
                "assert pathlib.Path(sys.prefix).name == 'relative_venv_task'\""
            ),
        )
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            try:
                runner = SandboxRunner(root="runs", use_venv=True)
                workdir = runner.prepare(task)
                result = runner.run_command(workdir, task.test_command)
            finally:
                os.chdir(old_cwd)

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_prepare_with_install_repo_installs_local_package_in_venv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "package_repo"
            (source / "samplepkg").mkdir(parents=True)
            (source / "samplepkg" / "__init__.py").write_text(
                "VALUE = 42\n",
                encoding="utf-8",
            )
            (source / "setup.py").write_text(
                "from setuptools import setup\n\n"
                "setup(name='samplepkg', version='0.0.1', packages=['samplepkg'])\n",
                encoding="utf-8",
            )
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
                task_id="install_repo_task",
                repo="local/package",
                local_repo_path=str(source),
                base_commit=base_commit,
                issue="Import package after editable install.",
                test_command="python -c 'import samplepkg; assert samplepkg.VALUE == 42'",
            )
            runner = SandboxRunner(
                root=root / "runs",
                use_venv=True,
                install_repo=True,
            )
            workdir = runner.prepare(task)
            result = runner.run_command(workdir, task.test_command)

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


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
