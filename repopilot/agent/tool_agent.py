from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from repopilot.agent.actions import AgentAction, parse_action
from repopilot.agent.loop import AgentRunResult
from repopilot.benchmark.task_loader import Task
from repopilot.memory.retrieve import KeywordMemoryRetriever
from repopilot.memory.schema import MemoryRecord
from repopilot.models.deepseek_client import ChatMessage
from repopilot.sandbox.runner import SandboxRunner
from repopilot.tools.search import search_code
from repopilot.trajectory.schema import Trajectory
from repopilot.verifier.pytest_verifier import CommandVerifier
from repopilot.verifier.result import VerifierResult


class ChatClient(Protocol):
    model: str

    def chat(self, messages: list[ChatMessage], temperature: float = 1.0) -> str:
        ...


@dataclass(frozen=True)
class ToolLoopConfig:
    max_steps: int = 12
    max_test_runs: int = 4
    max_observation_chars: int = 6000
    temperature: float = 1.0


class DeepSeekToolAgent:
    """Iterative tool-use coding agent.

    The model emits one JSON action per step. RepoPilot executes the action,
    records the observation, and sends it back to the model for the next step.
    """

    def __init__(
        self,
        runner: SandboxRunner,
        verifier: CommandVerifier,
        client: ChatClient,
        memory_retriever: KeywordMemoryRetriever | None = None,
        config: ToolLoopConfig | None = None,
    ) -> None:
        self.runner = runner
        self.verifier = verifier
        self.client = client
        self.memory_retriever = memory_retriever
        self.config = config or ToolLoopConfig()

    def run(self, task: Task) -> AgentRunResult:
        workdir = self.runner.prepare(task)
        trajectory = Trajectory(task_id=task.task_id, repo=task.repo, issue=task.issue)
        trajectory.add_step("prepare", f"Created sandbox at {workdir}")

        memories = self._retrieve_memories(task, trajectory)
        baseline = self.verifier.verify(workdir, task.test_command)
        trajectory.add_step(
            "verify_baseline",
            baseline.error_summary or f"returncode={baseline.returncode}",
            baseline.to_dict(),
        )

        messages = [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            ChatMessage(
                role="user",
                content=build_initial_prompt(task, workdir, memories, baseline),
            ),
        ]

        final_result = baseline
        test_runs = 1
        submitted = False

        for step in range(1, self.config.max_steps + 1):
            try:
                model_output = self.client.chat(
                    messages,
                    temperature=self.config.temperature,
                )
            except Exception as exc:
                trajectory.add_step(
                    "model_call_error",
                    f"{type(exc).__name__}: {exc}",
                    {"step": step, "model": self.client.model},
                )
                break
            try:
                action = parse_action(model_output)
            except ValueError as exc:
                observation = f"Invalid action: {exc}"
                trajectory.add_step(
                    "model_action_invalid",
                    _truncate(model_output, self.config.max_observation_chars),
                    {"step": step, "error": str(exc)},
                )
                messages.append(ChatMessage(role="assistant", content=model_output))
                messages.append(ChatMessage(role="user", content=observation))
                continue

            trajectory.add_step(
                "model_action",
                _truncate(model_output, self.config.max_observation_chars),
                {"step": step, "action": action.to_dict()},
            )

            observation, final_result, did_submit, test_runs = self._execute_action(
                action=action,
                task=task,
                workdir=workdir,
                current_result=final_result,
                test_runs=test_runs,
            )
            submitted = submitted or did_submit
            trajectory.add_step(
                f"tool:{action.name}",
                _truncate(observation, self.config.max_observation_chars),
                {
                    "step": step,
                    "action": action.to_dict(),
                    "resolved": final_result.resolved,
                    "test_runs": test_runs,
                },
            )

            messages.append(ChatMessage(role="assistant", content=model_output))
            messages.append(ChatMessage(role="user", content=f"Observation:\n{observation}"))

            if did_submit:
                break

        if not submitted and self.runner.git_diff(workdir).strip():
            final_result = self.verifier.verify(workdir, task.test_command)
            trajectory.add_step(
                "verify_final_unsubmitted_patch",
                final_result.error_summary or f"resolved={final_result.resolved}",
                final_result.to_dict(),
            )

        final_patch = self.runner.git_diff(workdir)
        trajectory.final_patch = final_patch
        trajectory.resolved = final_result.resolved
        trajectory.verifier = final_result.to_dict()

        return AgentRunResult(
            task_id=task.task_id,
            resolved=final_result.resolved,
            patch=final_patch,
            workdir=workdir,
            trajectory=trajectory,
        )

    def _retrieve_memories(self, task: Task, trajectory: Trajectory) -> list[MemoryRecord]:
        if self.memory_retriever is None:
            return []
        memories = self.memory_retriever.retrieve(task.issue)
        trajectory.add_step(
            "retrieve_memory",
            f"Retrieved {len(memories)} memory record(s).",
            {"memory_ids": [memory.memory_id for memory in memories]},
        )
        return memories

    def _execute_action(
        self,
        action: AgentAction,
        task: Task,
        workdir: Path,
        current_result: VerifierResult,
        test_runs: int,
    ) -> tuple[str, VerifierResult, bool, int]:
        if action.name == "search_code":
            query = str(action.args.get("query", ""))
            limit = int(action.args.get("limit", 20))
            matches = search_code(workdir, query, limit=limit)
            return json.dumps(matches, indent=2), current_result, False, test_runs

        if action.name == "read_file":
            path = _required_str(action, "path")
            start = _optional_int(action.args.get("start"))
            end = _optional_int(action.args.get("end"))
            return _read_file_slice(self.runner, workdir, path, start, end), current_result, False, test_runs

        if action.name == "replace_text":
            path = _required_str(action, "path")
            old = _required_str(action, "old")
            new = _required_str_allow_empty(action, "new")
            result = self.runner.replace_text(workdir, path, old, new)
            observation = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
            return json.dumps(observation, indent=2), current_result, False, test_runs

        if action.name == "apply_patch":
            diff = _required_str(action, "diff")
            result = self.runner.apply_unified_diff(workdir, diff)
            observation = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
            return json.dumps(observation, indent=2), current_result, False, test_runs

        if action.name == "run_tests":
            if test_runs >= self.config.max_test_runs:
                return (
                    f"Test budget exhausted: {test_runs}/{self.config.max_test_runs}.",
                    current_result,
                    False,
                    test_runs,
                )
            command = str(action.args.get("command") or task.test_command)
            verification = self.verifier.verify(workdir, command)
            return json.dumps(verification.to_dict(), indent=2), verification, False, test_runs + 1

        if action.name == "get_diff":
            return self.runner.git_diff(workdir), current_result, False, test_runs

        if action.name == "submit":
            verification = self.verifier.verify(workdir, task.test_command)
            observation = {
                "resolved": verification.resolved,
                "verifier": verification.to_dict(),
                "diff": self.runner.git_diff(workdir),
            }
            return json.dumps(observation, indent=2), verification, True, test_runs + 1

        raise ValueError(f"Unsupported action: {action.name}")


SYSTEM_PROMPT = """You are RepoPilot-CL, a repository-level coding agent.

Return exactly one JSON object per turn. Do not use markdown.

Allowed actions:
- {"action": "search_code", "args": {"query": "...", "limit": 20}, "thought": "..."}
- {"action": "read_file", "args": {"path": "...", "start": 1, "end": 120}, "thought": "..."}
- {"action": "replace_text", "args": {"path": "...", "old": "...", "new": "..."}, "thought": "..."}
- {"action": "apply_patch", "args": {"diff": "..."}, "thought": "..."}
- {"action": "run_tests", "args": {}, "thought": "..."}
- {"action": "get_diff", "args": {}, "thought": "..."}
- {"action": "submit", "args": {}, "thought": "..."}

Use minimal patches. Prefer replace_text for small local edits because it
avoids fragile diff formatting. Use apply_patch for larger multi-location
edits. Run tests after applying a patch. Submit only when the diff is ready to
be evaluated.
"""


def build_initial_prompt(
    task: Task,
    workdir: Path,
    memories: list[MemoryRecord],
    baseline: VerifierResult,
) -> str:
    files = sorted(path.name for path in workdir.iterdir() if path.is_file())
    memories_text = "No prior memories."
    if memories:
        memories_text = "\n".join(
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
            f"Files at repository root:\n{json.dumps(files, indent=2)}",
            f"Baseline verifier result:\n{json.dumps(baseline.to_dict(), indent=2)}",
            f"Retrieved memories:\n{memories_text}",
            "Start by inspecting the relevant file(s).",
        ]
    )


def _read_file_slice(
    runner: SandboxRunner,
    workdir: Path,
    path: str,
    start: int | None,
    end: int | None,
) -> str:
    content = runner.read_file(workdir, path)
    lines = content.splitlines()
    first = 1 if start is None else max(1, start)
    last = len(lines) if end is None else min(len(lines), end)
    selected = lines[first - 1 : last]
    return "\n".join(f"{line_number}: {line}" for line_number, line in enumerate(selected, start=first))


def _required_str(action: AgentAction, key: str) -> str:
    value = action.args.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Action `{action.name}` requires string arg `{key}`.")
    return value


def _required_str_allow_empty(action: AgentAction, key: str) -> str:
    value = action.args.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Action `{action.name}` requires string arg `{key}`.")
    return value


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[truncated]"
