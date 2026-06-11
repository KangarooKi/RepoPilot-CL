from pathlib import Path
import tempfile
import unittest

from repopilot.agent.loop import CodingAgent, PatchCandidate, ScriptedPatchProvider
from repopilot.benchmark.task_loader import load_task
from repopilot.reranker.score import RuleBasedPatchReranker
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

    def test_agent_reranks_candidates_before_verification(self) -> None:
        task = load_task(Path("tasks/toy/divide_by_zero/task.json"))
        provider = StaticPatchProvider(
            [
                PatchCandidate(
                    candidate_id="bad-assert",
                    diff=_replace_diff(
                        "calc.py",
                        "    return a / b\n",
                        "    assert b != 0\n    return a / b\n",
                    ),
                    rationale="Assert on zero divisor.",
                ),
                PatchCandidate(
                    candidate_id="good-guard",
                    diff=_replace_diff(
                        "calc.py",
                        "    return a / b\n",
                        "    if b == 0:\n        return None\n    return a / b\n",
                    ),
                    rationale="Return None on zero divisor.",
                ),
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = SandboxRunner(root=temp_dir)
            verifier = CommandVerifier(runner)
            agent = CodingAgent(
                runner,
                verifier,
                provider,
                patch_reranker=RuleBasedPatchReranker(),
            )
            result = agent.run(task)

        rerank_step = [
            step for step in result.trajectory.steps if step.action == "rerank_patches"
        ][0]
        apply_steps = [
            step for step in result.trajectory.steps if step.action == "apply_patch"
        ]

        self.assertTrue(result.resolved)
        self.assertEqual(
            rerank_step.metadata["ranked_candidate_ids"],
            ["good-guard", "bad-assert"],
        )
        self.assertEqual(apply_steps[0].metadata["candidate_id"], "good-guard")

    def test_agent_reverts_failed_candidate_before_next_candidate(self) -> None:
        task = load_task(Path("tasks/toy/divide_by_zero/task.json"))
        provider = StaticPatchProvider(
            [
                PatchCandidate(
                    candidate_id="bad-assert",
                    diff=_replace_diff(
                        "calc.py",
                        "    return a / b\n",
                        "    assert b != 0\n    return a / b\n",
                    ),
                    rationale="Assert on zero divisor.",
                ),
                PatchCandidate(
                    candidate_id="good-guard",
                    diff=_replace_diff(
                        "calc.py",
                        "    return a / b\n",
                        "    if b == 0:\n        return None\n    return a / b\n",
                    ),
                    rationale="Return None on zero divisor.",
                ),
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = SandboxRunner(root=temp_dir)
            verifier = CommandVerifier(runner)
            agent = CodingAgent(runner, verifier, provider, patch_reranker=None)
            result = agent.run(task)

        apply_ids = [
            step.metadata["candidate_id"]
            for step in result.trajectory.steps
            if step.action == "apply_patch"
        ]
        revert_ids = [
            step.metadata["candidate_id"]
            for step in result.trajectory.steps
            if step.action == "revert_candidate"
        ]

        self.assertTrue(result.resolved)
        self.assertEqual(apply_ids, ["bad-assert", "good-guard"])
        self.assertEqual(revert_ids, ["bad-assert"])


class StaticPatchProvider:
    def __init__(self, candidates: list[PatchCandidate]) -> None:
        self.candidates = candidates

    def propose(self, task, workdir, runner, memories):
        return self.candidates


def _replace_diff(path: str, old: str, new: str) -> str:
    import difflib

    original = "def divide(a, b):\n" + old
    modified = "def divide(a, b):\n" + new
    return "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            modified.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )


if __name__ == "__main__":
    unittest.main()
