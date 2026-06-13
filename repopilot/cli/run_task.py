from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from repopilot.agent.tool_agent import DeepSeekToolAgent, ToolLoopConfig
from repopilot.agent.loop import CodingAgent, ScriptedPatchProvider
from repopilot.agent.deepseek_provider import DeepSeekPatchProvider
from repopilot.benchmark.task_loader import load_task
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
    parser = argparse.ArgumentParser(description="Run one RepoPilot-CL task.")
    parser.add_argument("task", help="Path to task JSON.")
    parser.add_argument("--runs-dir", default="runs", help="Directory for sandboxes.")
    parser.add_argument("--repo-cache-dir", default=None)
    parser.add_argument("--clone-timeout-sec", type=int, default=600)
    parser.add_argument("--use-venv", action="store_true")
    parser.add_argument("--venv-root", default=None)
    parser.add_argument("--python-executable", default=None)
    parser.add_argument("--install-repo", action="store_true")
    parser.add_argument("--setup-command", default=None)
    parser.add_argument(
        "--provider",
        choices=["scripted", "deepseek", "deepseek-tools"],
        default="scripted",
        help="Patch provider to use.",
    )
    parser.add_argument("--model", default="deepseek-v4-flash", help="DeepSeek model name.")
    parser.add_argument(
        "--temperature",
        type=float,
        default=1.0,
        help="DeepSeek sampling temperature.",
    )
    parser.add_argument(
        "--base-url",
        default="https://api.deepseek.com",
        help="DeepSeek API base URL.",
    )
    parser.add_argument(
        "--reasoning-effort",
        default="max",
        help="DeepSeek reasoning effort, for example high or max.",
    )
    parser.add_argument(
        "--no-thinking",
        action="store_true",
        help="Disable DeepSeek thinking mode.",
    )
    parser.add_argument(
        "--ca-bundle",
        default=None,
        help="Path to a CA bundle for DeepSeek HTTPS requests.",
    )
    parser.add_argument(
        "--allow-insecure-ssl",
        action="store_true",
        help="Disable TLS certificate verification for local debugging only.",
    )
    parser.add_argument(
        "--api-timeout-sec",
        type=int,
        default=120,
        help="Overall timeout for each DeepSeek API call.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=12,
        help="Maximum model/tool steps for deepseek-tools.",
    )
    parser.add_argument(
        "--max-test-runs",
        type=int,
        default=4,
        help="Maximum verifier test runs for deepseek-tools.",
    )
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
        default="data/trajectories/latest.jsonl",
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
        help="Disable memory retrieval and learning for this run.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    task = load_task(args.task)
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
    memory_runtime = (
        MemoryRuntime.disabled()
        if args.no_memory
        else MemoryRuntime.from_path(args.memory_store, top_k=args.memory_top_k)
    )
    memory_retriever = memory_runtime.retriever()
    critic_hints = (
        load_prompt_hint_map(args.critic_hints_file)
        if args.critic_hints_file
        else {}
    )
    critic_hint = critic_hints.get(task.task_id)
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
            agent = DeepSeekToolAgent(
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
        else:
            patch_provider = DeepSeekPatchProvider(
                client,
                temperature=args.temperature,
                num_candidates=args.num_candidates,
                context_builder=None if args.no_context else build_context_builder(args),
                use_context=not args.no_context,
                critic_hint=critic_hint,
            )
            agent = CodingAgent(
                runner,
                verifier,
                patch_provider,
                memory_retriever=memory_retriever,
                patch_reranker=patch_reranker,
            )
    else:
        patch_provider = ScriptedPatchProvider()
        agent = CodingAgent(
            runner,
            verifier,
            patch_provider,
            memory_retriever=memory_retriever,
            patch_reranker=patch_reranker,
        )
    result = agent.run(task)
    learned_memory = memory_runtime.learn(result.trajectory)

    TrajectoryLogger(args.trajectory_log).append(result.trajectory)
    print(
        json.dumps(
            {
                "task_id": result.task_id,
                "resolved": result.resolved,
                "workdir": str(Path(result.workdir).resolve()),
                "patch": result.patch,
                "memory_id": learned_memory.memory_id if learned_memory else None,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if result.resolved else 1


def build_reranker(
    name: str,
    model_path: str,
) -> RuleBasedPatchReranker | LearnedPatchReranker | None:
    if name == "none":
        return None
    if name == "learned":
        return LearnedPatchReranker(load_model(model_path))
    return RuleBasedPatchReranker()


def build_context_builder(args: argparse.Namespace) -> ContextPackBuilder:
    return ContextPackBuilder(
        max_queries=args.context_max_queries,
        max_snippets=args.context_max_snippets,
        context_lines=args.context_lines,
        max_chars=args.context_max_chars,
    )


if __name__ == "__main__":
    raise SystemExit(main())
