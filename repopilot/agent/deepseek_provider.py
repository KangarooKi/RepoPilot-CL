from __future__ import annotations

import re
from pathlib import Path

from repopilot.agent.loop import PatchCandidate
from repopilot.benchmark.task_loader import Task
from repopilot.context.pack import ContextPackBuilder
from repopilot.memory.schema import MemoryRecord
from repopilot.models.deepseek_client import ChatMessage, DeepSeekClient
from repopilot.sandbox.runner import SandboxRunner


class DeepSeekPatchProvider:
    """Patch provider that asks DeepSeek for one or more unified diff candidates."""

    def __init__(
        self,
        client: DeepSeekClient,
        temperature: float = 1.0,
        num_candidates: int = 1,
        context_builder: ContextPackBuilder | None = None,
        use_context: bool = True,
    ) -> None:
        self.client = client
        self.temperature = temperature
        self.num_candidates = max(1, num_candidates)
        self.context_builder = (
            context_builder if context_builder is not None else ContextPackBuilder()
        )
        self.use_context = use_context

    def propose(
        self,
        task: Task,
        workdir: Path,
        runner: SandboxRunner,
        memories: list[MemoryRecord],
    ) -> list[PatchCandidate]:
        prompt = build_patch_prompt(
            task,
            workdir,
            runner,
            memories,
            context_builder=self.context_builder,
            use_context=self.use_context,
        )
        candidates: list[PatchCandidate] = []
        seen_diffs: set[str] = set()
        for index in range(self.num_candidates):
            content = self.client.chat(
                [
                    ChatMessage(
                        role="system",
                        content=(
                            "You are RepoPilot-CL, a coding agent. Return only a valid "
                            "unified diff patch. Do not wrap the answer in markdown."
                        ),
                    ),
                    ChatMessage(
                        role="user",
                        content=_candidate_prompt(prompt, index, self.num_candidates),
                    ),
                ],
                temperature=self.temperature,
            )
            diff = extract_unified_diff(content)
            if not diff or diff in seen_diffs:
                continue
            seen_diffs.add(diff)
            candidates.append(
                PatchCandidate(
                    candidate_id=f"deepseek-{index}",
                    diff=diff,
                    rationale="DeepSeek-generated candidate patch.",
                    model=self.client.model,
                )
            )
        return candidates


def build_patch_prompt(
    task: Task,
    workdir: Path,
    runner: SandboxRunner,
    memories: list[MemoryRecord],
    context_builder: ContextPackBuilder | None = None,
    use_context: bool = True,
) -> str:
    context_block = "Selected repository context:\nContext packing disabled."
    if use_context:
        builder = context_builder or ContextPackBuilder()
        context_pack = builder.build(
            task=task,
            workdir=workdir,
            runner=runner,
            memories=memories,
        )
        context_block = "\n\n".join(
            [
                f"Context search queries:\n{context_pack.queries}",
                "Selected repository context:\n" + context_pack.render(),
            ]
        )

    memory_block = "No prior memories."
    if memories:
        memory_block = "\n".join(
            [
                (
                    f"- {memory.memory_id}: {memory.issue_summary}; "
                    f"resolved={memory.resolved}; "
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
            context_block,
            (
                "Produce a minimal unified diff that fixes the issue. The patch "
                "must apply with `git apply` from the repository root. Use exact "
                "repository-relative file paths. If selected context is provided, "
                "prefer paths exactly as shown there; do not invent legacy or "
                "alternative filenames."
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


def _candidate_prompt(prompt: str, index: int, total: int) -> str:
    if total == 1:
        return prompt
    return "\n\n".join(
        [
            prompt,
            (
                f"Candidate {index + 1} of {total}: produce an independent minimal "
                "patch candidate. Prefer a different repair strategy if multiple "
                "reasonable fixes exist."
            ),
        ]
    )
