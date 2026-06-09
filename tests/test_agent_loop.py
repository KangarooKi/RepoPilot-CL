from pathlib import Path
import tempfile
import unittest

from repopilot.agent.loop import CodingAgent, ScriptedPatchProvider
from repopilot.benchmark.task_loader import load_task
from repopilot.sandbox.runner import SandboxRunner
from repopilot.verifier.pytest_verifier import CommandVerifier


class AgentLoopTest(unittest.TestCase):
    def test_scripted_agent_solves_toy_task(self) -> None:
        task = load_task(Path("tasks/toy/divide_by_zero/task.json"))
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = SandboxRunner(root=temp_dir)
            verifier = CommandVerifier(runner)
            agent = CodingAgent(runner, verifier, ScriptedPatchProvider())
            result = agent.run(task)

        self.assertTrue(result.resolved)
        self.assertIn("if b == 0", result.patch)
        self.assertTrue(result.trajectory.resolved)


if __name__ == "__main__":
    unittest.main()

