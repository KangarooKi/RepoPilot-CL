from __future__ import annotations

import argparse
import json
from pathlib import Path

from repopilot.report.benchmark_compare import (
    compare_benchmark_reports,
    write_comparison_artifacts,
)
from repopilot.report.benchmark_report import load_report_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare two RepoPilot-CL benchmark report JSON files and render "
            "task-level gained/lost/still outcome transitions."
        )
    )
    parser.add_argument("--base", required=True, help="Base benchmark report JSON.")
    parser.add_argument(
        "--candidate",
        required=True,
        help="Candidate benchmark report JSON to compare against base.",
    )
    parser.add_argument("--base-name", default="base", help="Display name for base.")
    parser.add_argument(
        "--candidate-name",
        default="candidate",
        help="Display name for candidate.",
    )
    parser.add_argument(
        "--task-ids-file",
        default=None,
        help="Optional canonical task-id order file, one task id per line.",
    )
    parser.add_argument(
        "--require-same-tasks",
        action="store_true",
        help="Fail if base and candidate reports do not contain the same task ids.",
    )
    parser.add_argument(
        "--output-md",
        default="data/reports/benchmark_comparison.md",
        help="Markdown comparison output path.",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Optional structured comparison JSON output path.",
    )
    parser.add_argument(
        "--title",
        default="RepoPilot-CL Benchmark Comparison",
        help="Markdown report title.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    base = load_report_json(args.base)
    candidate = load_report_json(args.candidate)
    if args.require_same_tasks:
        _require_same_task_ids(base, candidate)
    task_order = _load_task_ids(args.task_ids_file) if args.task_ids_file else None
    comparison = compare_benchmark_reports(
        base,
        candidate,
        base_name=args.base_name,
        candidate_name=args.candidate_name,
        task_order=task_order,
    )
    write_comparison_artifacts(
        comparison,
        markdown_path=args.output_md,
        json_path=args.output_json,
        title=args.title,
    )
    print(json.dumps(comparison.to_dict(), indent=2))
    print(f"Markdown report: {args.output_md}")
    if args.output_json:
        print(f"JSON report: {args.output_json}")
    return 0


def _require_same_task_ids(base, candidate) -> None:
    base_ids = {task.task_id for task in base.tasks}
    candidate_ids = {task.task_id for task in candidate.tasks}
    if base_ids == candidate_ids:
        return
    missing = sorted(base_ids - candidate_ids)
    extra = sorted(candidate_ids - base_ids)
    parts = []
    if missing:
        parts.append(f"missing from candidate: {', '.join(missing)}")
    if extra:
        parts.append(f"extra in candidate: {', '.join(extra)}")
    raise SystemExit("Task sets differ; " + "; ".join(parts))


def _load_task_ids(path: str | Path) -> list[str]:
    task_ids: list[str] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            task_ids.append(stripped)
    return task_ids


if __name__ == "__main__":
    raise SystemExit(main())
