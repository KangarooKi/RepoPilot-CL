from __future__ import annotations

import argparse
import json
from pathlib import Path

from repopilot.report.benchmark_report import (
    load_report_json,
    merge_benchmark_reports,
    write_report_artifacts,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Merge RepoPilot-CL benchmark report JSON files with task-id "
            "deduplication and resolved-priority rescue semantics."
        )
    )
    parser.add_argument(
        "reports",
        nargs="+",
        help="Structured benchmark report JSON files to merge, in priority order.",
    )
    parser.add_argument(
        "--task-ids-file",
        default=None,
        help="Optional canonical task-id order file, one task id per line.",
    )
    parser.add_argument(
        "--require-task-count",
        type=int,
        default=None,
        help="Fail if the merged report does not contain this many unique tasks.",
    )
    parser.add_argument(
        "--output-md",
        default="data/reports/merged_benchmark_report.md",
        help="Markdown report output path.",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Optional structured report JSON output path.",
    )
    parser.add_argument(
        "--title",
        default="RepoPilot-CL Merged Benchmark Report",
        help="Markdown report title.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    reports = [load_report_json(path) for path in args.reports]
    task_order = _load_task_ids(args.task_ids_file) if args.task_ids_file else None
    merged = merge_benchmark_reports(reports, task_order=task_order)
    if args.require_task_count is not None and merged.total != args.require_task_count:
        raise SystemExit(
            f"Expected {args.require_task_count} tasks, found {merged.total}."
        )
    write_report_artifacts(
        merged,
        markdown_path=args.output_md,
        json_path=args.output_json,
        title=args.title,
    )
    print(json.dumps(merged.to_dict(), indent=2))
    print(f"Markdown report: {args.output_md}")
    if args.output_json:
        print(f"JSON report: {args.output_json}")
    return 0


def _load_task_ids(path: str | Path) -> list[str]:
    task_ids: list[str] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            task_ids.append(stripped)
    return task_ids


if __name__ == "__main__":
    raise SystemExit(main())
