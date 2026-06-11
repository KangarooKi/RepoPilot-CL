from __future__ import annotations

import argparse
import json

from repopilot.benchmark.runner import discover_task_files, filter_tasks, load_task_inputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect RepoPilot task files.")
    parser.add_argument("tasks", nargs="+", help="Task JSON/JSONL file(s) or glob(s).")
    parser.add_argument(
        "--input-format",
        choices=["repopilot", "swebench"],
        default="repopilot",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--repo-contains", default=None)
    parser.add_argument("--max-fail-to-pass", type=int, default=None)
    parser.add_argument("--max-pass-to-pass", type=int, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    files = discover_task_files(args.tasks)
    tasks = load_task_inputs(files, input_format=args.input_format)
    tasks = filter_tasks(
        tasks,
        repo_contains=args.repo_contains,
        max_fail_to_pass=args.max_fail_to_pass,
        max_pass_to_pass=args.max_pass_to_pass,
    )
    if args.limit is not None:
        tasks = tasks[: args.limit]
    summary = {
        "total": len(tasks),
        "tasks": [
            {
                "task_id": task.task_id,
                "repo": task.repo,
                "base_commit": task.base_commit,
                "repo_url": task.repo_url,
                "fail_to_pass": len(task.fail_to_pass_tests),
                "pass_to_pass": len(task.pass_to_pass_tests),
                "test_command": task.test_command,
            }
            for task in tasks
        ],
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
