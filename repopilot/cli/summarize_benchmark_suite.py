from __future__ import annotations

import argparse
import json

from repopilot.report.benchmark_report import load_report_json
from repopilot.report.benchmark_suite import (
    NamedBenchmarkReport,
    build_benchmark_suite,
    write_suite_artifacts,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize multiple RepoPilot-CL benchmark reports into one "
            "suite-level table for ablations and scale-out tracking."
        )
    )
    parser.add_argument(
        "--report",
        action="append",
        required=True,
        help="Named report in NAME=PATH form. Can be passed multiple times.",
    )
    parser.add_argument(
        "--baseline",
        default=None,
        help="Report name to use as baseline. Defaults to the first --report.",
    )
    parser.add_argument(
        "--require-same-tasks",
        action="store_true",
        help="Fail if any report does not share the baseline task ids.",
    )
    parser.add_argument(
        "--output-md",
        default="data/reports/benchmark_suite.md",
        help="Markdown suite report output path.",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Optional structured suite JSON output path.",
    )
    parser.add_argument(
        "--title",
        default="RepoPilot-CL Benchmark Suite",
        help="Markdown report title.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    named_reports = [_load_named_report(value) for value in args.report]
    suite = build_benchmark_suite(
        named_reports,
        title=args.title,
        baseline_name=args.baseline,
        require_same_tasks=args.require_same_tasks,
    )
    write_suite_artifacts(
        suite,
        markdown_path=args.output_md,
        json_path=args.output_json,
    )
    print(json.dumps(suite.to_dict(), indent=2))
    print(f"Markdown report: {args.output_md}")
    if args.output_json:
        print(f"JSON report: {args.output_json}")
    return 0


def _load_named_report(value: str) -> NamedBenchmarkReport:
    if "=" not in value:
        raise SystemExit("--report must use NAME=PATH form.")
    name, path = value.split("=", 1)
    name = name.strip()
    path = path.strip()
    if not name or not path:
        raise SystemExit("--report must use NAME=PATH form.")
    return NamedBenchmarkReport(name=name, path=path, report=load_report_json(path))


if __name__ == "__main__":
    raise SystemExit(main())
