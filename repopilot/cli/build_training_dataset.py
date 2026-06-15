from __future__ import annotations

import argparse
import json

from repopilot.training.examples import (
    build_training_examples,
    summarize_training_examples,
    write_training_examples,
    write_training_summary,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build RepoPilot-CL critic/reranker training examples from trajectory JSONL files."
        )
    )
    parser.add_argument("trajectories", nargs="+", help="Trajectory JSONL file(s).")
    parser.add_argument(
        "--output-jsonl",
        default="data/training/repopilot_training_examples.jsonl",
        help="Output JSONL path for training examples.",
    )
    parser.add_argument(
        "--output-summary-json",
        default=None,
        help="Optional structured summary JSON output path.",
    )
    parser.add_argument(
        "--output-summary-md",
        default=None,
        help="Optional Markdown summary output path.",
    )
    parser.add_argument(
        "--objective",
        action="append",
        choices=["critic", "reranker"],
        help=(
            "Training objective to include. Can be passed multiple times. "
            "Defaults to both critic and reranker."
        ),
    )
    filter_group = parser.add_mutually_exclusive_group()
    filter_group.add_argument(
        "--only-resolved",
        action="store_true",
        help="Keep only trajectories whose final patch passed verification.",
    )
    filter_group.add_argument(
        "--only-unresolved",
        action="store_true",
        help="Keep only trajectories whose final patch did not pass verification.",
    )
    parser.add_argument(
        "--include-empty-patch-reranker",
        action="store_true",
        help="Also emit reranker examples for trajectories that ended without a patch.",
    )
    parser.add_argument(
        "--max-signal-chars",
        type=int,
        default=1200,
        help="Maximum characters kept for baseline/final failure signals.",
    )
    parser.add_argument(
        "--max-patch-chars",
        type=int,
        default=6000,
        help="Maximum characters kept for candidate patches in reranker inputs.",
    )
    parser.add_argument(
        "--title",
        default="RepoPilot-CL Training Dataset Summary",
        help="Markdown summary title.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    examples = build_training_examples(
        args.trajectories,
        objectives=set(args.objective) if args.objective else None,
        include_resolved=not args.only_unresolved,
        include_unresolved=not args.only_resolved,
        include_empty_patch_reranker=args.include_empty_patch_reranker,
        max_signal_chars=args.max_signal_chars,
        max_patch_chars=args.max_patch_chars,
    )
    write_training_examples(examples, args.output_jsonl)
    summary = summarize_training_examples(examples, output=args.output_jsonl)
    write_training_summary(
        summary,
        output_json=args.output_summary_json,
        output_md=args.output_summary_md,
        title=args.title,
    )
    print(json.dumps(summary.to_dict(), indent=2, ensure_ascii=False))
    print(f"Training examples: {args.output_jsonl}")
    if args.output_summary_json:
        print(f"Summary JSON: {args.output_summary_json}")
    if args.output_summary_md:
        print(f"Summary Markdown: {args.output_summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
