from __future__ import annotations

import argparse
import json
from pathlib import Path

from repopilot.agent.loop import CodingAgent, ScriptedPatchProvider
from repopilot.benchmark.task_loader import load_task
from repopilot.sandbox.runner import SandboxRunner
from repopilot.trajectory.logger import TrajectoryLogger
from repopilot.verifier.pytest_verifier import CommandVerifier


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one RepoPilot-CL task.")
    parser.add_argument("task", help="Path to task JSON.")
    parser.add_argument("--runs-dir", default="runs", help="Directory for sandboxes.")
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
    agent = CodingAgent(runner, verifier, ScriptedPatchProvider())
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

