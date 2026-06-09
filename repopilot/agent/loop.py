from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from repopilot.benchmark.task_loader import Task
from repopilot.memory.retrieve import KeywordMemoryRetriever
from repopilot.memory.schema import MemoryRecord
from repopilot.sandbox.runner import SandboxRunner
from repopilot.trajectory.schema import Trajectory
from repopilot.verifier.pytest_verifier import CommandVerifier


@dataclass(frozen=True)
class PatchCandidate:
    candidate_id: str
    diff: str
    rationale: str
    model: str = "scripted"


@dataclass(frozen=True)
class AgentRunResult:
    task_id: str
    resolved: bool
    patch: str
    workdir: Path
    trajectory: Trajectory


class PatchProvider(Protocol):
    def propose(
        self,
        task: Task,
        workdir: Path,
        runner: SandboxRunner,
        memories: list[MemoryRecord],
    ) -> list[PatchCandidate]:
        ...


class ScriptedPatchProvider:
    """A tiny provider used to keep the MVP executable without an API key."""

    def propose(
        self,
        task: Task,
        workdir: Path,
        runner: SandboxRunner,
        memories: list[MemoryRecord],
    ) -> list[PatchCandidate]:
        if "divide" not in task.issue.lower():
            return []

        for relative_path in task.initial_files:
            content = runner.read_file(workdir, relative_path)
            old = "    return a / b\n"
            new = "    if b == 0:\n        return None\n    return a / b\n"
            if old in content:
                diff = _single_file_replace_diff(relative_path, content, content.replace(old, new))
                return [
                    PatchCandidate(
                        candidate_id="scripted-divide-zero",
                        diff=diff,
                        rationale="Add an explicit zero divisor guard.",
                    )
                ]
        return []


class CodingAgent:
    def __init__(
        self,
        runner: SandboxRunner,
        verifier: CommandVerifier,
        patch_provider: PatchProvider,
        memory_retriever: KeywordMemoryRetriever | None = None,
    ) -> None:
        self.runner = runner
        self.verifier = verifier
        self.patch_provider = patch_provider
        self.memory_retriever = memory_retriever

    def run(self, task: Task) -> AgentRunResult:
        workdir = self.runner.prepare(task)
        trajectory = Trajectory(task_id=task.task_id, repo=task.repo, issue=task.issue)
        trajectory.add_step("prepare", f"Created sandbox at {workdir}")

        memories = []
        if self.memory_retriever is not None:
            memories = self.memory_retriever.retrieve(task.issue)
            trajectory.add_step(
                "retrieve_memory",
                f"Retrieved {len(memories)} memory record(s).",
                {"memory_ids": [memory.memory_id for memory in memories]},
            )

        baseline = self.verifier.verify(workdir, task.test_command)
        trajectory.add_step(
            "verify_baseline",
            baseline.error_summary or f"returncode={baseline.returncode}",
            baseline.to_dict(),
        )

        candidates = self.patch_provider.propose(task, workdir, self.runner, memories)
        trajectory.add_step("propose_patch", f"Generated {len(candidates)} candidate(s).")

        best_patch = ""
        final_result = baseline
        for candidate in candidates:
            apply_result = self.runner.apply_unified_diff(workdir, candidate.diff)
            trajectory.add_step(
                "apply_patch",
                apply_result.stderr or candidate.rationale,
                {
                    "candidate_id": candidate.candidate_id,
                    "returncode": apply_result.returncode,
                    "model": candidate.model,
                },
            )
            if apply_result.returncode != 0:
                continue

            verification = self.verifier.verify(workdir, task.test_command)
            trajectory.add_step(
                "verify_candidate",
                verification.error_summary or f"resolved={verification.resolved}",
                {
                    "candidate_id": candidate.candidate_id,
                    **verification.to_dict(),
                },
            )
            best_patch = self.runner.git_diff(workdir)
            final_result = verification
            if verification.resolved:
                break

        trajectory.final_patch = best_patch
        trajectory.resolved = final_result.resolved
        trajectory.verifier = final_result.to_dict()

        return AgentRunResult(
            task_id=task.task_id,
            resolved=final_result.resolved,
            patch=best_patch,
            workdir=workdir,
            trajectory=trajectory,
        )


def _single_file_replace_diff(path: str, old: str, new: str) -> str:
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    import difflib

    return "".join(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )

