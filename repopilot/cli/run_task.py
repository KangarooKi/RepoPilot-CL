from __future__ import annotations

import argparse
import json
from pathlib import Path

from repopilot.agent.tool_agent import DeepSeekToolAgent, ToolLoopConfig
from repopilot.agent.loop import CodingAgent, ScriptedPatchProvider
from repopilot.agent.deepseek_provider import DeepSeekPatchProvider
from repopilot.benchmark.task_loader import load_task
from repopilot.models.deepseek_client import DeepSeekClient
from repopilot.sandbox.runner import SandboxRunner
from repopilot.trajectory.logger import TrajectoryLogger
from repopilot.verifier.pytest_verifier import CommandVerifier


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one RepoPilot-CL task.")
    parser.add_argument("task", help="Path to task JSON.")
    parser.add_argument("--runs-dir", default="runs", help="Directory for sandboxes.")
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
        "--trajectory-log",
        default="data/trajectories/latest.jsonl",
        help="JSONL file for trajectory output.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    task = load_task(args.task)
    runner = SandboxRunner(root=args.runs_dir)
    verifier = CommandVerifier(runner)

    if args.provider in {"deepseek", "deepseek-tools"}:
        client = DeepSeekClient(
            model=args.model,
            base_url=args.base_url,
            reasoning_effort=args.reasoning_effort,
            thinking_enabled=not args.no_thinking,
        )
        if args.provider == "deepseek-tools":
            agent = DeepSeekToolAgent(
                runner,
                verifier,
                client,
                config=ToolLoopConfig(
                    max_steps=args.max_steps,
                    max_test_runs=args.max_test_runs,
                    temperature=args.temperature,
                ),
            )
        else:
            patch_provider = DeepSeekPatchProvider(client, temperature=args.temperature)
            agent = CodingAgent(runner, verifier, patch_provider)
    else:
        patch_provider = ScriptedPatchProvider()
        agent = CodingAgent(runner, verifier, patch_provider)
    result = agent.run(task)

    TrajectoryLogger(args.trajectory_log).append(result.trajectory)
    print(
        json.dumps(
            {
                "task_id": result.task_id,
                "resolved": result.resolved,
                "workdir": str(Path(result.workdir).resolve()),
                "patch": result.patch,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if result.resolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
