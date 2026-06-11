from __future__ import annotations

import argparse
import json
from pathlib import Path

from repopilot.experiment.runner import (
    render_markdown_report,
    run_experiment,
    select_variants,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run RepoPilot-CL benchmark ablations and render a report."
    )
    parser.add_argument("tasks", nargs="+", help="Task JSON file(s) or glob pattern(s).")
    parser.add_argument(
        "--variants",
        default="baseline,context,memory,memory_reranker",
        help="Comma-separated variants: baseline,context,memory,memory_reranker.",
    )
    parser.add_argument("--output-dir", default="data/experiments/latest")
    parser.add_argument(
        "--input-format",
        choices=["repopilot", "swebench"],
        default="repopilot",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--repo-contains", default=None)
    parser.add_argument("--max-fail-to-pass", type=int, default=None)
    parser.add_argument("--max-pass-to-pass", type=int, default=None)
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
    )
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--base-url", default="https://api.deepseek.com")
    parser.add_argument("--reasoning-effort", default="max")
    parser.add_argument("--no-thinking", action="store_true")
    parser.add_argument("--ca-bundle", default=None)
    parser.add_argument("--allow-insecure-ssl", action="store_true")
    parser.add_argument("--max-steps", type=int, default=12)
    parser.add_argument("--max-test-runs", type=int, default=4)
    parser.add_argument("--context-max-queries", type=int, default=8)
    parser.add_argument("--context-max-snippets", type=int, default=6)
    parser.add_argument("--context-lines", type=int, default=12)
    parser.add_argument("--context-max-chars", type=int, default=12000)
    parser.add_argument(
        "--num-candidates",
        type=int,
        default=3,
        help="Candidate count for reranker variants.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_dir = Path(args.output_dir)
    variants = select_variants(
        [name.strip() for name in args.variants.split(",") if name.strip()],
        num_candidates=args.num_candidates,
    )
    result = run_experiment(
        tasks=args.tasks,
        common_args=_common_benchmark_args(args),
        output_dir=output_dir,
        variants=variants,
    )
    summary_path = output_dir / "experiment_summary.json"
    report_path = output_dir / "report.md"
    summary_path.write_text(
        json.dumps(result.to_dict(), indent=2),
        encoding="utf-8",
    )
    report_path.write_text(render_markdown_report(result), encoding="utf-8")
    print(json.dumps(result.to_dict(), indent=2))
    print(f"Report: {report_path}")
    return 0


def _common_benchmark_args(args: argparse.Namespace) -> list[str]:
    common = [
        "--input-format",
        args.input_format,
        "--provider",
        args.provider,
        "--model",
        args.model,
        "--temperature",
        str(args.temperature),
        "--base-url",
        args.base_url,
        "--reasoning-effort",
        args.reasoning_effort,
        "--clone-timeout-sec",
        str(args.clone_timeout_sec),
        "--max-steps",
        str(args.max_steps),
        "--max-test-runs",
        str(args.max_test_runs),
        "--context-max-queries",
        str(args.context_max_queries),
        "--context-max-snippets",
        str(args.context_max_snippets),
        "--context-lines",
        str(args.context_lines),
        "--context-max-chars",
        str(args.context_max_chars),
    ]
    optional_values = [
        ("--limit", args.limit),
        ("--repo-contains", args.repo_contains),
        ("--max-fail-to-pass", args.max_fail_to_pass),
        ("--max-pass-to-pass", args.max_pass_to_pass),
        ("--repo-cache-dir", args.repo_cache_dir),
        ("--venv-root", args.venv_root),
        ("--python-executable", args.python_executable),
        ("--setup-command", args.setup_command),
        ("--ca-bundle", args.ca_bundle),
    ]
    for flag, value in optional_values:
        if value is not None:
            common.extend([flag, str(value)])
    if args.use_venv:
        common.append("--use-venv")
    if args.install_repo:
        common.append("--install-repo")
    if args.no_thinking:
        common.append("--no-thinking")
    if args.allow_insecure_ssl:
        common.append("--allow-insecure-ssl")
    return common


if __name__ == "__main__":
    raise SystemExit(main())
