from __future__ import annotations

import argparse
import json
from pathlib import Path

from repopilot.agent.deepseek_provider import DeepSeekPatchProvider
from repopilot.agent.loop import CodingAgent, ScriptedPatchProvider
from repopilot.agent.tool_agent import DeepSeekToolAgent, ToolLoopConfig
from repopilot.benchmark.runner import discover_task_files, run_tasks
from repopilot.benchmark.task_loader import Task
from repopilot.models.deepseek_client import DeepSeekClient
from repopilot.sandbox.runner import SandboxRunner
from repopilot.trajectory.logger import TrajectoryLogger
from repopilot.verifier.pytest_verifier import CommandVerifier


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a RepoPilot-CL task suite.")
    parser.add_argument("tasks", nargs="+", help="Task JSON file(s) or glob pattern(s).")
    parser.add_argument("--runs-dir", default="runs", help="Directory for sandboxes.")
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
    parser.add_argument("--max-steps", type=int, default=12)
    parser.add_argument("--max-test-runs", type=int, default=4)
    parser.add_argument(
        "--trajectory-log",
        default="data/trajectories/benchmark.jsonl",
        help="JSONL file for trajectory output.",
    )
    parser.add_argument(
        "--output",
        default="data/benchmarks/latest_summary.json",
        help="JSON file for benchmark summary.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    task_files = discover_task_files(args.tasks)
    if not task_files:
        raise SystemExit("No task files matched.")

    trajectory_logger = TrajectoryLogger(args.trajectory_log)

    def run_one(task: Task):
        runner = SandboxRunner(root=args.runs_dir)
        verifier = CommandVerifier(runner)
        agent = build_agent(args, runner, verifier)
        result = agent.run(task)
        trajectory_logger.append(result.trajectory)
        return result

    summary = run_tasks(task_files, run_one)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary.to_dict(), indent=2), encoding="utf-8")
    print(json.dumps(summary.to_dict(), indent=2))
    return 0 if summary.resolved == summary.total else 1


def build_agent(args, runner: SandboxRunner, verifier: CommandVerifier):
    if args.provider in {"deepseek", "deepseek-tools"}:
        client = DeepSeekClient(
            model=args.model,
            base_url=args.base_url,
            reasoning_effort=args.reasoning_effort,
            thinking_enabled=not args.no_thinking,
            ca_bundle=args.ca_bundle,
            allow_insecure_ssl=args.allow_insecure_ssl,
        )
        if args.provider == "deepseek-tools":
            return DeepSeekToolAgent(
                runner,
                verifier,
                client,
                config=ToolLoopConfig(
                    max_steps=args.max_steps,
                    max_test_runs=args.max_test_runs,
                    temperature=args.temperature,
                ),
            )
        return CodingAgent(runner, verifier, DeepSeekPatchProvider(client, args.temperature))
    return CodingAgent(runner, verifier, ScriptedPatchProvider())


if __name__ == "__main__":
    raise SystemExit(main())

