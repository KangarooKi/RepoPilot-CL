from __future__ import annotations

import argparse
import json

from repopilot.report.benchmark_report import (
    load_benchmark_report,
    write_report_artifacts,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a RepoPilot-CL benchmark summary and trajectory report."
    )
    parser.add_argument("--summary", required=True, help="Benchmark summary JSON path.")
    parser.add_argument(
        "--trajectory",
        required=True,
        help="Trajectory JSONL path produced by run_benchmark.",
    )
    parser.add_argument(
        "--output-md",
        default="data/reports/benchmark_report.md",
        help="Markdown report output path.",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Optional structured report JSON output path.",
    )
    parser.add_argument(
        "--title",
        default="RepoPilot-CL Benchmark Report",
        help="Markdown report title.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = load_benchmark_report(args.summary, args.trajectory)
    write_report_artifacts(
        report,
        markdown_path=args.output_md,
        json_path=args.output_json,
        title=args.title,
    )
    print(json.dumps(report.to_dict(), indent=2))
    print(f"Markdown report: {args.output_md}")
    if args.output_json:
        print(f"JSON report: {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
