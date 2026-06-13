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


class TimeoutChatClient:
    model = "timeout-model"

    def chat(self, messages: list[ChatMessage], temperature: float = 1.0) -> str:
        raise TimeoutError("request timed out")


class FlakyChatClient(FakeChatClient):
    model = "flaky-tool-model"

    def __init__(self, actions: list[dict[str, object]]) -> None:
        super().__init__(actions)
        self.failed_once = False

    def chat(self, messages: list[ChatMessage], temperature: float = 1.0) -> str:
        if not self.failed_once:
            self.failed_once = True
            raise TimeoutError("first call timed out")
        return super().chat(messages, temperature=temperature)


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

    def test_tool_agent_records_model_call_errors(self) -> None:
        task = load_task(Path("tasks/toy/divide_by_zero/task.json"))

        with tempfile.TemporaryDirectory() as temp_dir:
            runner = SandboxRunner(root=temp_dir)
            verifier = CommandVerifier(runner)
            agent = DeepSeekToolAgent(
                runner,
                verifier,
                TimeoutChatClient(),
                config=ToolLoopConfig(max_steps=2, max_test_runs=2),
            )
            result = agent.run(task)

        self.assertFalse(result.resolved)
        self.assertTrue(
            any(step.action == "model_call_error" for step in result.trajectory.steps)
        )

    def test_tool_agent_retries_model_call_errors(self) -> None:
        client = FlakyChatClient(
            [
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
                {"action": "submit", "args": {}, "thought": "verify and submit"},
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
                config=ToolLoopConfig(
                    max_steps=4,
                    max_test_runs=3,
                    max_model_retries=1,
                ),
            )
            result = agent.run(task)

        errors = [
            step for step in result.trajectory.steps if step.action == "model_call_error"
        ]
        self.assertTrue(result.resolved)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].metadata["retriable"])

    def test_tool_agent_returns_tool_errors_to_model(self) -> None:
        client = FakeChatClient(
            [
                {
                    "action": "read_file",
                    "args": {"path": "missing.py"},
                    "thought": "try the guessed path",
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
                    "thought": "use the actual file",
                },
                {"action": "submit", "args": {}, "thought": "verify and submit"},
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
                config=ToolLoopConfig(max_steps=5, max_test_runs=3),
            )
            result = agent.run(task)

        read_steps = [
            step for step in result.trajectory.steps if step.action == "tool:read_file"
        ]
        self.assertTrue(result.resolved)
        self.assertIn("Tool action error", read_steps[0].observation)
        self.assertIn("FileNotFoundError", read_steps[0].metadata["tool_error"])

    def test_tool_agent_includes_failure_critic_hint_in_initial_prompt(self) -> None:
        client = FakeChatClient(
            [
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
                    "thought": "use critic hint",
                },
                {"action": "submit", "args": {}, "thought": "verify and submit"},
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
                critic_hint="Previous run missed calc.py; inspect it first.",
                config=ToolLoopConfig(max_steps=4, max_test_runs=3),
            )
            result = agent.run(task)

        initial_prompt = client.messages[0][1].content
        self.assertTrue(result.resolved)
        self.assertIn("Failure critic hints", initial_prompt)
        self.assertIn("missed calc.py", initial_prompt)


if __name__ == "__main__":
    unittest.main()
