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


if __name__ == "__main__":
    unittest.main()

