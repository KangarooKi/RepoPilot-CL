from __future__ import annotations

import argparse
import json
from pathlib import Path

from repopilot.critic.failure import (
    build_failure_hint,
    load_failed_trajectories,
    render_failure_hints_markdown,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build failure critic hints from RepoPilot trajectories."
    )
    parser.add_argument(
        "trajectories",
        nargs="+",
        help="Trajectory JSONL files produced by run_task or run_benchmark.",
    )
    parser.add_argument(
        "--task-id",
        action="append",
        default=[],
        help="Only build hints for this task id. May be passed multiple times.",
    )
    parser.add_argument(
        "--include-resolved",
        action="store_true",
        help="Also emit hints for resolved trajectories.",
    )
    parser.add_argument(
        "--output-json",
        required=True,
        help="Structured failure hint JSON output.",
    )
    parser.add_argument(
        "--output-md",
        default=None,
        help="Optional Markdown report output.",
    )
    parser.add_argument(
        "--title",
        default="Failure Critic Hints",
        help="Markdown report title.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    task_ids = {task_id.strip() for task_id in args.task_id if task_id.strip()} or None
    trajectories = load_failed_trajectories(
        args.trajectories,
        task_ids=task_ids,
        include_resolved=args.include_resolved,
    )
    hints = [build_failure_hint(trajectory) for trajectory in trajectories]

    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "sources": args.trajectories,
        "hints": [hint.to_dict() for hint in hints],
    }
    output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if args.output_md is not None:
        output_md = Path(args.output_md)
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(
            render_failure_hints_markdown(
                hints,
                title=args.title,
                source=", ".join(args.trajectories),
            ),
            encoding="utf-8",
        )

    print(json.dumps({"hints": len(hints), "output_json": str(output_json)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
