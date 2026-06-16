from __future__ import annotations

import argparse
import json
from pathlib import Path

from repopilot.critic.learned import (
    evaluate_predictions,
    load_jsonl,
    reference_map,
    render_eval_markdown,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate learned critic JSON predictions against SFT targets."
    )
    parser.add_argument("predictions_jsonl", help="Prediction JSONL from predict_critic_lora.")
    parser.add_argument(
        "--reference-jsonl",
        default=None,
        help="Optional critic SFT JSONL if predictions do not carry reference targets.",
    )
    parser.add_argument("--output-json", default=None, help="Optional metrics JSON output.")
    parser.add_argument("--output-md", default=None, help="Optional Markdown report output.")
    parser.add_argument(
        "--focus-k",
        type=int,
        action="append",
        default=[],
        help="Focus file recall cutoff. May be passed multiple times.",
    )
    parser.add_argument("--title", default="Learned Critic Evaluation")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    prediction_rows = load_jsonl(args.predictions_jsonl)
    if not prediction_rows:
        raise SystemExit(f"No predictions loaded from {args.predictions_jsonl}")
    references = None
    if args.reference_jsonl:
        references = reference_map(load_jsonl(args.reference_jsonl))
    focus_ks = tuple(args.focus_k or [1, 3, 5])
    summary = evaluate_predictions(
        prediction_rows,
        references=references,
        focus_ks=focus_ks,
    )
    payload = summary.to_dict()
    if args.output_json is not None:
        output_json = Path(args.output_json)
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if args.output_md is not None:
        output_md = Path(args.output_md)
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(
            render_eval_markdown(summary, title=args.title, source=args.predictions_jsonl),
            encoding="utf-8",
        )
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
