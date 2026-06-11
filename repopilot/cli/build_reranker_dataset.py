from __future__ import annotations

import argparse
import json

from repopilot.reranker.dataset import (
    load_reranker_examples,
    write_reranker_examples,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build RepoPilot-Reranker JSONL data from trajectory logs."
    )
    parser.add_argument("trajectories", nargs="+", help="Trajectory JSONL file(s).")
    parser.add_argument(
        "--output",
        default="data/reranker/reranker_examples.jsonl",
        help="Output JSONL path.",
    )
    parser.add_argument(
        "--only-resolved",
        action="store_true",
        help="Keep only examples whose candidate patch passed verification.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    examples = load_reranker_examples(args.trajectories)
    if args.only_resolved:
        examples = [example for example in examples if example.resolved]
    write_reranker_examples(examples, args.output)
    summary = {
        "examples": len(examples),
        "resolved": sum(1 for example in examples if example.resolved),
        "regression": sum(1 for example in examples if example.regression),
        "output": args.output,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
