from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from repopilot.agent.deepseek_provider import DeepSeekPatchProvider
from repopilot.agent.loop import CodingAgent, ScriptedPatchProvider
from repopilot.agent.tool_agent import DeepSeekToolAgent, ToolLoopConfig
from repopilot.benchmark.runner import (
    discover_task_files,
    filter_tasks,
    load_task_inputs,
    run_tasks,
)
from repopilot.benchmark.task_loader import Task
from repopilot.context.pack import ContextPackBuilder
from repopilot.critic.failure import load_prompt_hint_map
from repopilot.memory.runtime import MemoryRuntime
from repopilot.models.deepseek_client import DeepSeekClient
from repopilot.reranker.model import LearnedPatchReranker, load_model
from repopilot.reranker.score import RuleBasedPatchReranker
from repopilot.sandbox.runner import SandboxRunner
from repopilot.trajectory.logger import TrajectoryLogger
from repopilot.verifier.pytest_verifier import CommandVerifier


DEFAULT_MEMORY_STORE = "data/memory/repopilot_memory.jsonl"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a RepoPilot-CL task suite.")
    parser.add_argument("tasks", nargs="+", help="Task JSON file(s) or glob pattern(s).")
    parser.add_argument(
        "--input-format",
        choices=["repopilot", "swebench"],
        default="repopilot",
        help="Input task format.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Maximum tasks to run.")
    parser.add_argument(
        "--task-id",
        action="append",
        default=[],
        help="Run only the specified task id. May be passed multiple times.",
    )
    parser.add_argument(
        "--task-ids-file",
        default=None,
        help="Newline-delimited task ids to run, for rescue/hard-case subsets.",
    )
    parser.add_argument("--repo-contains", default=None)
    parser.add_argument("--max-fail-to-pass", type=int, default=None)
    parser.add_argument("--max-pass-to-pass", type=int, default=None)
    parser.add_argument("--runs-dir", default="runs", help="Directory for sandboxes.")
    parser.add_argument(
        "--repo-cache-dir",
        default=None,
        help="Optional directory for cached GitHub repo clones.",
    )
    parser.add_argument("--clone-timeout-sec", type=int, default=600)
    parser.add_argument("--use-venv", action="store_true")
    parser.add_argument("--venv-root", default=None)
    parser.add_argument("--python-executable", default=None)
    parser.add_argument("--install-repo", action="store_true")
    parser.add_argument(
        "--setup-command",
        default=None,
        help="Override setup command for every loaded task.",
    )
    parser.add_argument(
        "--provider",
        choices=["scripted", "deepseek", "deepseek-tools"],
        default="scripted",
        help="Patch provider to use.",
    )
    parser.add_argument("--model", default="deepseek-v4-flash", help="DeepSeek model name.")
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--base-url", default="https://api.deepseek.com")
    parser.add_argument("--reasoning-effort", default="max")
    parser.add_argument("--no-thinking", action="store_true")
    parser.add_argument("--ca-bundle", default=None)
    parser.add_argument("--allow-insecure-ssl", action="store_true")
    parser.add_argument(
        "--api-timeout-sec",
        type=int,
        default=120,
        help="Overall timeout for each DeepSeek API call.",
    )
    parser.add_argument("--max-steps", type=int, default=12)
    parser.add_argument("--max-test-runs", type=int, default=4)
    parser.add_argument(
        "--model-retries",
        type=int,
        default=0,
        help="Retry failed DeepSeek tool-agent model calls before giving up.",
    )
    parser.add_argument(
        "--num-candidates",
        type=int,
        default=1,
        help="Number of DeepSeek patch candidates for non-tool providers.",
    )
    parser.add_argument("--context-max-queries", type=int, default=8)
    parser.add_argument("--context-max-snippets", type=int, default=6)
    parser.add_argument("--context-lines", type=int, default=12)
    parser.add_argument("--context-max-chars", type=int, default=12000)
    parser.add_argument(
        "--no-context",
        action="store_true",
        help="Disable repository context packing for non-tool DeepSeek runs.",
    )
    parser.add_argument(
        "--reranker",
        choices=["rule", "learned", "none"],
        default="rule",
        help="Patch reranker for candidate-based providers.",
    )
    parser.add_argument(
        "--reranker-model",
        default="data/reranker/reranker_model.json",
        help="Model JSON path for --reranker learned.",
    )
    parser.add_argument(
        "--trajectory-log",
        default="data/trajectories/benchmark.jsonl",
        help="JSONL file for trajectory output.",
    )
    parser.add_argument(
        "--critic-hints-file",
        default=None,
        help="Optional failure critic hint JSON produced by build_failure_hints.",
    )
    parser.add_argument(
        "--memory-store",
        default=DEFAULT_MEMORY_STORE,
        help="JSONL file used for continual-learning memory.",
    )
    parser.add_argument("--memory-top-k", type=int, default=3)
    parser.add_argument(
        "--no-memory",
        action="store_true",
        help="Disable memory retrieval and learning for this benchmark run.",
    )
    parser.add_argument(
        "--output",
        default="data/benchmarks/latest_summary.json",
        help="JSON file for benchmark summary.",
    )
    parser.add_argument(
        "--fail-on-unresolved",
        action="store_true",
        help="Exit with status 1 if any task is unresolved.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    task_files = discover_task_files(args.tasks)
    if not task_files:
        raise SystemExit("No task files matched.")
    tasks = load_task_inputs(task_files, input_format=args.input_format)
    task_ids = _load_task_id_filter(args.task_id, args.task_ids_file)
    tasks = filter_tasks(
        tasks,
        task_ids=task_ids,
        repo_contains=args.repo_contains,
        max_fail_to_pass=args.max_fail_to_pass,
        max_pass_to_pass=args.max_pass_to_pass,
    )
    if args.limit is not None:
        tasks = tasks[: args.limit]
    if not tasks:
        raise SystemExit("No tasks loaded.")

    trajectory_logger = TrajectoryLogger(args.trajectory_log)
    critic_hints = (
        load_prompt_hint_map(args.critic_hints_file)
        if args.critic_hints_file
        else {}
    )
    memory_runtime = (
        MemoryRuntime.disabled()
        if args.no_memory
        else MemoryRuntime.from_path(args.memory_store, top_k=args.memory_top_k)
    )

    def run_one(task: Task):
        if args.setup_command is not None:
            task = replace(task, setup_command=args.setup_command)
        runner = SandboxRunner(
            root=args.runs_dir,
            repo_cache_dir=args.repo_cache_dir,
            clone_timeout_sec=args.clone_timeout_sec,
            use_venv=args.use_venv,
            venv_root=args.venv_root,
            python_executable=args.python_executable,
            install_repo=args.install_repo,
        )
        verifier = CommandVerifier(runner)
        agent = build_agent(
            args,
            runner,
            verifier,
            memory_runtime.retriever(),
            critic_hint=critic_hints.get(task.task_id),
        )
        result = agent.run(task)
        trajectory_logger.append(result.trajectory)
        memory_runtime.learn(result.trajectory)
        return result

    summary = run_tasks(tasks, run_one)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary.to_dict(), indent=2), encoding="utf-8")
    print(json.dumps(summary.to_dict(), indent=2))
    if args.fail_on_unresolved and summary.resolved != summary.total:
        return 1
    return 0


def build_agent(
    args,
    runner: SandboxRunner,
    verifier: CommandVerifier,
    memory_retriever,
    critic_hint: str | None = None,
):
    patch_reranker = build_reranker(args.reranker, args.reranker_model)
    if args.provider in {"deepseek", "deepseek-tools"}:
        client = DeepSeekClient(
            model=args.model,
            base_url=args.base_url,
            reasoning_effort=args.reasoning_effort,
            thinking_enabled=not args.no_thinking,
            ca_bundle=args.ca_bundle,
            allow_insecure_ssl=args.allow_insecure_ssl,
            timeout_sec=args.api_timeout_sec,
        )
        if args.provider == "deepseek-tools":
            return DeepSeekToolAgent(
                runner,
                verifier,
                client,
                memory_retriever=memory_retriever,
                critic_hint=critic_hint,
                config=ToolLoopConfig(
                    max_steps=args.max_steps,
                    max_test_runs=args.max_test_runs,
                    max_model_retries=args.model_retries,
                    temperature=args.temperature,
                ),
            )
        return CodingAgent(
            runner,
            verifier,
            DeepSeekPatchProvider(
                client,
                temperature=args.temperature,
                num_candidates=args.num_candidates,
                context_builder=None if args.no_context else build_context_builder(args),
                use_context=not args.no_context,
                critic_hint=critic_hint,
            ),
            memory_retriever=memory_retriever,
            patch_reranker=patch_reranker,
        )
    return CodingAgent(
        runner,
        verifier,
        ScriptedPatchProvider(),
        memory_retriever=memory_retriever,
        patch_reranker=patch_reranker,
    )


def build_reranker(
    name: str,
    model_path: str,
) -> RuleBasedPatchReranker | LearnedPatchReranker | None:
    if name == "none":
        return None
    if name == "learned":
        return LearnedPatchReranker(load_model(model_path))
    return RuleBasedPatchReranker()


def build_context_builder(args) -> ContextPackBuilder:
    return ContextPackBuilder(
        max_queries=args.context_max_queries,
        max_snippets=args.context_max_snippets,
        context_lines=args.context_lines,
        max_chars=args.context_max_chars,
    )


def _load_task_id_filter(
    task_ids: list[str],
    task_ids_file: str | None,
) -> set[str] | None:
    selected = {task_id.strip() for task_id in task_ids if task_id.strip()}
    if task_ids_file is not None:
        with Path(task_ids_file).open("r", encoding="utf-8") as handle:
            selected.update(
                line.strip()
                for line in handle
                if line.strip() and not line.lstrip().startswith("#")
            )
    return selected or None


if __name__ == "__main__":
    raise SystemExit(main())
