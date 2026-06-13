import unittest
import tempfile

from repopilot.agent.deepseek_provider import (
    DeepSeekPatchProvider,
    build_patch_prompt,
    extract_unified_diff,
)
from repopilot.benchmark.task_loader import load_task
from repopilot.models.deepseek_client import ChatMessage
from repopilot.sandbox.runner import SandboxRunner


class DeepSeekProviderTest(unittest.TestCase):
    def test_extract_unified_diff_from_markdown_fence(self) -> None:
        output = """Here is the patch:

```diff
diff --git a/calc.py b/calc.py
--- a/calc.py
+++ b/calc.py
@@ -1,2 +1,4 @@
 def divide(a, b):
+    if b == 0:
+        return None
     return a / b
```
"""

        diff = extract_unified_diff(output)

        self.assertTrue(diff.startswith("diff --git"))
        self.assertIn("if b == 0", diff)

    def test_patch_provider_generates_multiple_unique_candidates(self) -> None:
        client = FakePatchClient(
            [
                _patch("    if b == 0:\n        return None\n    return a / b\n"),
                _patch("    return None if b == 0 else a / b\n"),
            ]
        )
        task = load_task("tasks/toy/divide_by_zero/task.json")
        provider = DeepSeekPatchProvider(client, num_candidates=2)
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = SandboxRunner(root=temp_dir)
            workdir = runner.prepare(task)
            candidates = provider.propose(task, workdir, runner, memories=[])

        self.assertEqual(
            [candidate.candidate_id for candidate in candidates],
            ["deepseek-0", "deepseek-1"],
        )
        self.assertEqual(len(client.messages), 2)
        self.assertIn("Candidate 2 of 2", client.messages[1][-1].content)

    def test_build_patch_prompt_includes_context_pack(self) -> None:
        task = load_task("tasks/toy/divide_by_zero/task.json")
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = SandboxRunner(root=temp_dir)
            workdir = runner.prepare(task)
            prompt = build_patch_prompt(task, workdir, runner, memories=[])

        self.assertIn("Selected repository context", prompt)
        self.assertIn("calc.py", prompt)
        self.assertIn("def divide", prompt)

    def test_build_patch_prompt_can_disable_context_pack(self) -> None:
        task = load_task("tasks/toy/divide_by_zero/task.json")
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = SandboxRunner(root=temp_dir)
            workdir = runner.prepare(task)
            prompt = build_patch_prompt(
                task,
                workdir,
                runner,
                memories=[],
                use_context=False,
            )

        self.assertIn("Context packing disabled", prompt)
        self.assertNotIn("Context search queries", prompt)
        self.assertNotIn("def divide", prompt)

    def test_build_patch_prompt_includes_failure_critic_hint(self) -> None:
        task = load_task("tasks/toy/divide_by_zero/task.json")
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = SandboxRunner(root=temp_dir)
            workdir = runner.prepare(task)
            prompt = build_patch_prompt(
                task,
                workdir,
                runner,
                memories=[],
                critic_hint="Focus on calc.py before patching.",
            )

        self.assertIn("Failure critic hints", prompt)
        self.assertIn("Focus on calc.py", prompt)


class FakePatchClient:
    model = "fake-deepseek"

    def __init__(self, outputs: list[str]) -> None:
        self.outputs = outputs
        self.messages: list[list[ChatMessage]] = []

    def chat(self, messages: list[ChatMessage], temperature: float = 1.0) -> str:
        self.messages.append(list(messages))
        return self.outputs.pop(0)


def _patch(replacement: str) -> str:
    added_lines = "".join(f"+{line}\n" for line in replacement.splitlines())
    return (
        "diff --git a/calc.py b/calc.py\n"
        "--- a/calc.py\n"
        "+++ b/calc.py\n"
        "@@ -1,2 +1,4 @@\n"
        " def divide(a, b):\n"
        "-    return a / b\n"
        f"{added_lines}"
    )


if __name__ == "__main__":
    unittest.main()
