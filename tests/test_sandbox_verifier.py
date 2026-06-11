from pathlib import Path
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
