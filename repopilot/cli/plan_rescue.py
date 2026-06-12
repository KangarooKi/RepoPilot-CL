from __future__ import annotations

import argparse
import json
import shlex

from repopilot.benchmark.rescue import (
    load_rescue_cases,
    write_rescue_markdown,
    write_rescue_task_ids,
)


DEFAULT_SETUP_COMMAND = (
    "python -m pip install 'pytest<8' 'click<8.2' 'numpy<2' "
    "'scipy<1.10' 'pandas<2' simplejson pytz pytest-mock pytest-timeout "
    "pytest-rerunfailures pytest-remotedata"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a hard-case rescue plan from a benchmark report."
    )
    parser.add_argument("--report", required=True, help="Benchmark report JSON.")
    parser.add_argument(
        "--failure-type",
        action="append",
        default=[],
        help="Only include this failure type. May be passed multiple times.",
    )
    parser.add_argument(
        "--output-task-ids",
        default="data/rescue/unresolved_task_ids.txt",
        help="Newline-delimited unresolved task id output.",
    )
    parser.add_argument(
        "--output-md",
        default=None,
        help="Optional Markdown rescue plan output.",
    )
    parser.add_argument(
        "--benchmark-input",
        default="data/swebench/lite_dev_10.jsonl",
        help="Task JSONL path to use in the recommended rerun command.",
    )
    parser.add_argument("--input-format", default="swebench")
    parser.add_argument("--repo-cache-dir", default="data/repos")
    parser.add_argument("--runs-dir", default="runs_rescue")
    parser.add_argument("--trajectory-log", default="data/trajectories/rescue.jsonl")
    parser.add_argument("--memory-store", default="data/memory/rescue_memory.jsonl")
    parser.add_argument("--output", default="data/benchmarks/rescue_summary.json")
    parser.add_argument("--provider", default="deepseek-tools")
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--reasoning-effort", default="max")
    parser.add_argument("--temperature", default="1.0")
    parser.add_argument("--api-timeout-sec", default="180")
    parser.add_argument("--max-steps", default="24")
    parser.add_argument("--max-test-runs", default="8")
    parser.add_argument("--model-retries", default="1")
    parser.add_argument("--setup-command", default=DEFAULT_SETUP_COMMAND)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    failure_types = set(args.failure_type) if args.failure_type else None
    cases = load_rescue_cases(args.report, failure_types=failure_types)
    write_rescue_task_ids(cases, args.output_task_ids)
    command = _recommended_command(args)
    if args.output_md is not None:
        write_rescue_markdown(
            cases,
            args.output_md,
            source_report=args.report,
            task_ids_path=args.output_task_ids,
            recommended_command=command,
        )
    print(
        json.dumps(
            {
                "source_report": args.report,
                "task_ids": [case.task_id for case in cases],
                "task_ids_path": args.output_task_ids,
                "markdown_path": args.output_md,
                "recommended_command": command,
            },
            indent=2,
        )
    )
    return 0


def _recommended_command(args: argparse.Namespace) -> str:
    command_lines = [
        _shell_line("python3", "-m", "repopilot.cli.run_benchmark", args.benchmark_input),
        _shell_line("--input-format", args.input_format),
        _shell_line("--task-ids-file", args.output_task_ids),
        _shell_line("--repo-cache-dir", args.repo_cache_dir),
        _shell_line("--use-venv"),
        _shell_line("--install-repo"),
        _shell_line("--setup-command", args.setup_command),
        _shell_line("--provider", args.provider),
        _shell_line("--model", args.model),
        _shell_line("--reasoning-effort", args.reasoning_effort),
        _shell_line("--temperature", str(args.temperature)),
        _shell_line("--api-timeout-sec", str(args.api_timeout_sec)),
        _shell_line("--max-steps", str(args.max_steps)),
        _shell_line("--max-test-runs", str(args.max_test_runs)),
        _shell_line("--model-retries", str(args.model_retries)),
        _shell_line("--runs-dir", args.runs_dir),
        _shell_line("--trajectory-log", args.trajectory_log),
        _shell_line("--memory-store", args.memory_store),
        _shell_line("--output", args.output),
    ]
    return " \\\n  ".join(command_lines)


def _shell_line(*parts: str) -> str:
    return " ".join(shlex.quote(part) for part in parts)


if __name__ == "__main__":
    raise SystemExit(main())
