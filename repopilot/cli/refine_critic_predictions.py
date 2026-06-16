from __future__ import annotations

import argparse
import json

from repopilot.critic.learned import load_jsonl
from repopilot.critic.refine import (
    refine_prediction_rows_with_evidence,
    write_prediction_rows_jsonl,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Apply retrieval-evidence focus expansion to learned critic predictions."
        )
    )
    parser.add_argument("predictions_jsonl", help="One-shot critic prediction JSONL.")
    parser.add_argument(
        "--refinement-jsonl",
        required=True,
        help="Refinement input JSONL with repository evidence metadata.",
    )
    parser.add_argument("--output-jsonl", required=True, help="Refined prediction JSONL.")
    parser.add_argument("--max-focus-files", type=int, default=8)
    parser.add_argument(
        "--keep-original",
        type=int,
        default=1,
        help="Number of original focus files to keep before evidence-expanded paths.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    prediction_rows = load_jsonl(args.predictions_jsonl)
    if not prediction_rows:
        raise SystemExit(f"No predictions loaded from {args.predictions_jsonl}")
    refinement_rows = load_jsonl(args.refinement_jsonl)
    if not refinement_rows:
        raise SystemExit(f"No refinement rows loaded from {args.refinement_jsonl}")
    rows = refine_prediction_rows_with_evidence(
        prediction_rows,
        refinement_rows,
        max_focus_files=args.max_focus_files,
        keep_original=args.keep_original,
    )
    write_prediction_rows_jsonl(rows, args.output_jsonl)
    print(
        json.dumps(
            {
                "examples": len(rows),
                "output_jsonl": args.output_jsonl,
                "strategy": "retrieval_evidence_focus_expansion",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
