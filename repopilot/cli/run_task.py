from __future__ import annotations

import argparse
import json
from dataclasses import replace
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
