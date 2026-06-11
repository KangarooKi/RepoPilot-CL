from __future__ import annotations

import argparse
import json

from repopilot.reranker.dataset import load_reranker_dataset
from repopilot.reranker.model import save_model, train_logistic_reranker


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train a lightweight RepoPilot patch reranker."
    )
    parser.add_argument("dataset", help="Reranker example JSONL file.")
    parser.add_argument(
        "--model-output",
        default="data/reranker/reranker_model.json",
        help="Output model JSON path.",
    )
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--learning-rate", type=float, default=0.5)
    parser.add_argument("--l2", type=float, default=0.001)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    examples = load_reranker_dataset(args.dataset)
    model = train_logistic_reranker(
        examples,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        l2=args.l2,
    )
    save_model(model, args.model_output)
    summary = {
        "model_output": args.model_output,
        **model.metrics,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
