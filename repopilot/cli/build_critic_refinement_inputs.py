from __future__ import annotations

import argparse
import json

from repopilot.critic.learned import load_jsonl
from repopilot.critic.refine import (
    build_refinement_rows,
    load_repo_map,
    write_refinement_jsonl,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build second-pass Test-Time-Critic refinement inputs from one-shot "
            "critic predictions and optional repository search evidence."
        )
    )
    parser.add_argument("predictions_jsonl", help="One-shot critic prediction JSONL.")
    parser.add_argument(
        "--source-jsonl",
        required=True,
        help="Original critic SFT JSONL used to recover issue inputs and references.",
    )
    parser.add_argument("--output-jsonl", required=True, help="Refinement input JSONL.")
    parser.add_argument(
        "--repo-map-json",
        default=None,
        help=(
            "Optional JSON map from task_id/repo/repo_slug to local repository roots. "
            "Also accepts {'tasks': {...}, 'repos': {...}}."
        ),
    )
    parser.add_argument(
        "--repo-root-template",
        default=None,
        help=(
            "Optional template for repository roots. Available placeholders: "
            "{task_id}, {repo}, {repo_slug}."
        ),
    )
    parser.add_argument("--max-examples", type=int, default=None)
    parser.add_argument("--max-queries", type=int, default=10)
    parser.add_argument("--max-snippets", type=int, default=8)
    parser.add_argument("--context-lines", type=int, default=12)
    parser.add_argument("--max-evidence-chars", type=int, default=12000)
    parser.add_argument("--max-index-file-size", type=int, default=250000)
    parser.add_argument(
        "--max-neighbor-files",
        type=int,
        default=4,
        help="Neighbor files to add around each predicted focus file.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    prediction_rows = load_jsonl(args.predictions_jsonl, max_examples=args.max_examples)
    if not prediction_rows:
        raise SystemExit(f"No predictions loaded from {args.predictions_jsonl}")
    source_rows = load_jsonl(args.source_jsonl)
    if not source_rows:
        raise SystemExit(f"No source rows loaded from {args.source_jsonl}")
    rows = build_refinement_rows(
        prediction_rows,
        source_rows,
        repo_map=load_repo_map(args.repo_map_json),
        repo_root_template=args.repo_root_template,
        max_examples=args.max_examples,
        max_queries=args.max_queries,
        max_snippets=args.max_snippets,
        context_lines=args.context_lines,
        max_evidence_chars=args.max_evidence_chars,
        max_index_file_size=args.max_index_file_size,
        max_neighbor_files=args.max_neighbor_files,
    )
    summary = write_refinement_jsonl(rows, args.output_jsonl)
    print(json.dumps(summary.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
