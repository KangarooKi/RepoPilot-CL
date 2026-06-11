import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from repopilot.agent.loop import CodingAgent, PatchCandidate
from repopilot.benchmark.task_loader import load_task
from repopilot.cli.build_reranker_dataset import main as build_dataset_main
from repopilot.reranker.dataset import examples_from_trajectory_payload
from repopilot.sandbox.runner import SandboxRunner
from repopilot.trajectory.logger import TrajectoryLogger
from repopilot.verifier.pytest_verifier import CommandVerifier


class RerankerDatasetTest(unittest.TestCase):
    def test_examples_from_trajectory_payload_reads_verified_candidates(self) -> None:
        payload = {
            "task_id": "toy",
            "repo": "toy/repo",
            "issue": "Fix divide by zero.",
            "steps": [
                {
                    "action": "retrieve_memory",
                    "observation": "Retrieved 1 memory record.",
                    "metadata": {"memory_ids": ["mem-1"]},
                },
                {
                    "action": "verify_baseline",
                    "observation": "ZeroDivisionError",
                    "metadata": {"resolved": False},
                },
                {
                    "action": "verify_candidate",
                    "observation": "resolved=True",
                    "metadata": {
                        "candidate_id": "c1",
                        "candidate_patch": "diff --git a/calc.py b/calc.py\n",
                        "resolved": True,
                        "regression": False,
                    },
                },
            ],
        }

        examples = examples_from_trajectory_payload(payload)

        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0].task_id, "toy")
        self.assertEqual(examples[0].candidate_id, "c1")
        self.assertEqual(examples[0].failing_tests, "ZeroDivisionError")
        self.assertEqual(examples[0].retrieved_memory, "memory_ids=mem-1")
        self.assertTrue(examples[0].resolved)

    def test_build_dataset_cli_from_agent_trajectory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            task = load_task("tasks/toy/divide_by_zero/task.json")
            runner = SandboxRunner(root=root / "runs")
            verifier = CommandVerifier(runner)
            agent = CodingAgent(
                runner,
                verifier,
                StaticPatchProvider(
                    [
                        PatchCandidate(
                            candidate_id="good",
                            diff=_replace_diff(
                                "calc.py",
                                "    return a / b\n",
                                "    if b == 0:\n        return None\n    return a / b\n",
                            ),
                            rationale="guard zero",
                        )
                    ]
                ),
            )
            result = agent.run(task)
            trajectory_path = root / "trajectory.jsonl"
            output_path = root / "dataset.jsonl"
            TrajectoryLogger(trajectory_path).append(result.trajectory)

            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = build_dataset_main(
                    [str(trajectory_path), "--output", str(output_path)]
                )
            rows = [
                json.loads(line)
                for line in output_path.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["task_id"], "toy_divide_by_zero")
        self.assertEqual(rows[0]["candidate_id"], "good")
        self.assertTrue(rows[0]["resolved"])
        self.assertIn("if b == 0", rows[0]["candidate_patch"])


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
