from __future__ import annotations

import argparse
import json

from repopilot.report.artifact_validation import (
    validate_artifacts,
    write_validation_artifacts,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate RepoPilot-CL benchmark artifacts for internal consistency, "
            "including reports, comparisons, suite summaries, and run manifests."
        )
    )
    parser.add_argument(
        "--report",
        action="append",
        default=[],
        help="Benchmark report JSON to validate. Can be passed multiple times.",
    )
    parser.add_argument(
        "--comparison",
        action="append",
        default=[],
        help="Benchmark comparison JSON to validate. Can be passed multiple times.",
    )
    parser.add_argument(
        "--suite",
        action="append",
        default=[],
        help="Benchmark suite summary JSON to validate. Can be passed multiple times.",
    )
    parser.add_argument(
        "--manifest",
        action="append",
        default=[],
        help="Run manifest JSON to validate. Can be passed multiple times.",
    )
    parser.add_argument(
        "--output-md",
        default="data/reports/artifact_validation.md",
        help="Markdown validation report output path.",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Optional structured validation JSON output path.",
    )
    parser.add_argument(
        "--title",
        default="RepoPilot-CL Artifact Validation",
        help="Markdown report title.",
    )
    parser.add_argument(
        "--no-fail",
        action="store_true",
        help="Always exit 0 even if validation checks fail.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = validate_artifacts(
        reports=args.report,
        comparisons=args.comparison,
        suites=args.suite,
        manifests=args.manifest,
    )
    write_validation_artifacts(
        report,
        markdown_path=args.output_md,
        json_path=args.output_json,
        title=args.title,
    )
    print(json.dumps(report.to_dict(), indent=2))
    print(f"Markdown validation report: {args.output_md}")
    if args.output_json:
        print(f"JSON validation report: {args.output_json}")
    return 0 if report.passed or args.no_fail else 1


if __name__ == "__main__":
    raise SystemExit(main())
