import json
from pathlib import Path
import tempfile
import unittest

from repopilot.agent.tool_agent import DeepSeekToolAgent, ToolLoopConfig
from repopilot.benchmark.task_loader import load_task
from repopilot.models.deepseek_client import ChatMessage
from repopilot.sandbox.runner import SandboxRunner
from repopilot.verifier.pytest_verifier import CommandVerifier


class FakeChatClient:
    model = "fake-tool-model"

    def __init__(self, actions: list[dict[str, object]]) -> None:
        self.actions = actions
        self.messages: list[list[ChatMessage]] = []

    def chat(self, messages: list[ChatMessage], temperature: float = 1.0) -> str:
        self.messages.append(list(messages))
        if not self.actions:
            return json.dumps({"action": "submit", "args": {}, "thought": "done"})
        return json.dumps(self.actions.pop(0))


class ToolAgentTest(unittest.TestCase):
    def test_tool_agent_solves_toy_task_with_action_loop(self) -> None:
        patch = (
            "diff --git a/calc.py b/calc.py\n"
            "--- a/calc.py\n"
            "+++ b/calc.py\n"
            "@@ -1,2 +1,4 @@\n"
            " def divide(a, b):\n"
            "+    if b == 0:\n"
            "+        return None\n"
            "     return a / b\n"
        )
        client = FakeChatClient(
            [
                {
                    "action": "read_file",
                    "args": {"path": "calc.py", "start": 1, "end": 20},
                    "thought": "inspect the implementation",
                },
                {
                    "action": "apply_patch",
                    "args": {"diff": patch},
                    "thought": "guard zero division",
                },
                {"action": "run_tests", "args": {}, "thought": "verify fix"},
                {"action": "submit", "args": {}, "thought": "tests passed"},
            ]
        )
        task = load_task(Path("tasks/toy/divide_by_zero/task.json"))

        with tempfile.TemporaryDirectory() as temp_dir:
            runner = SandboxRunner(root=temp_dir)
            verifier = CommandVerifier(runner)
            agent = DeepSeekToolAgent(
                runner,
                verifier,
                client,
                config=ToolLoopConfig(max_steps=8, max_test_runs=4),
            )
            result = agent.run(task)

        self.assertTrue(result.resolved)
        self.assertIn("if b == 0", result.patch)
        self.assertTrue(any(step.action == "tool:apply_patch" for step in result.trajectory.steps))
        self.assertGreaterEqual(len(client.messages), 4)

    def test_tool_agent_solves_toy_task_with_replace_text(self) -> None:
        client = FakeChatClient(
            [
                {
                    "action": "read_file",
                    "args": {"path": "calc.py", "start": 1, "end": 20},
                    "thought": "inspect the implementation",
                },
                {
                    "action": "replace_text",
                    "args": {
                        "path": "calc.py",
                        "old": "    return a / b\n",
                        "new": (
                            "    if b == 0:\n"
                            "        return None\n"
                            "    return a / b\n"
                        ),
                    },
                    "thought": "guard zero division",
                },
                {"action": "run_tests", "args": {}, "thought": "verify fix"},
                {"action": "submit", "args": {}, "thought": "tests passed"},
            ]
        )
        task = load_task(Path("tasks/toy/divide_by_zero/task.json"))

        with tempfile.TemporaryDirectory() as temp_dir:
            runner = SandboxRunner(root=temp_dir)
            verifier = CommandVerifier(runner)
            agent = DeepSeekToolAgent(
                runner,
                verifier,
                client,
                config=ToolLoopConfig(max_steps=8, max_test_runs=4),
            )
            result = agent.run(task)

        self.assertTrue(result.resolved)
        self.assertIn("if b == 0", result.patch)
        self.assertTrue(any(step.action == "tool:replace_text" for step in result.trajectory.steps))


if __name__ == "__main__":
    unittest.main()
