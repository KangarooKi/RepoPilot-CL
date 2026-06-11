from __future__ import annotations

import re
from pathlib import Path

from repopilot.agent.loop import PatchCandidate
from repopilot.benchmark.task_loader import Task
from repopilot.memory.schema import MemoryRecord
from repopilot.models.deepseek_client import ChatMessage, DeepSeekClient
from repopilot.sandbox.runner import SandboxRunner


class DeepSeekPatchProvider:
    """Patch provider that asks DeepSeek for a unified diff candidate."""

    def __init__(self, client: DeepSeekClient, temperature: float = 1.0) -> None:
        self.client = client
        self.temperature = temperature

    def propose(
        self,
        task: Task,
        workdir: Path,
        runner: SandboxRunner,
        memories: list[MemoryRecord],
    ) -> list[PatchCandidate]:
        prompt = build_patch_prompt(task, workdir, runner, memories)
        content = self.client.chat(
            [
                ChatMessage(
                    role="system",
                    content=(
                        "You are RepoPilot-CL, a coding agent. Return only a valid "
                        "unified diff patch. Do not wrap the answer in markdown."
                    ),
                ),
                ChatMessage(role="user", content=prompt),
            ],
            temperature=self.temperature,
        )
        diff = extract_unified_diff(content)
        if not diff:
            return []
        return [
            PatchCandidate(
                candidate_id="deepseek-0",
                diff=diff,
                rationale="DeepSeek-generated candidate patch.",
                model=self.client.model,
            )
        ]


def build_patch_prompt(
    task: Task,
    workdir: Path,
    runner: SandboxRunner,
    memories: list[MemoryRecord],
) -> str:
    files = []
    for relative_path in sorted(task.initial_files):
        content = runner.read_file(workdir, relative_path)
        files.append(f"### {relative_path}\n```text\n{content}\n```")

    memory_block = "No prior memories."
    if memories:
        memory_block = "\n".join(
            [
                (
                    f"- {memory.memory_id}: {memory.issue_summary}; "
                    f"error={memory.error_signature}; files={memory.touched_files}; "
                    f"pattern={memory.patch_pattern}"
                )
                for memory in memories
            ]
        )

    return "\n\n".join(
        [
            f"Task ID: {task.task_id}",
            f"Repository: {task.repo}",
            f"Issue:\n{task.issue}",
            f"Test command:\n{task.test_command}",
            f"Relevant memories:\n{memory_block}",
            "Repository files:\n" + "\n\n".join(files),
            (
                "Produce a minimal unified diff that fixes the issue. The patch "
                "must apply with `git apply` from the repository root."
            ),
        ]
    )


def extract_unified_diff(text: str) -> str:
    fence_match = re.search(r"```(?:diff|patch)?\s*(.*?)```", text, flags=re.S)
    candidate = fence_match.group(1) if fence_match else text

    lines = candidate.strip().splitlines()
    for index, line in enumerate(lines):
        if line.startswith("diff --git ") or line.startswith("--- "):
            return "\n".join(lines[index:]).strip() + "\n"
    return ""
