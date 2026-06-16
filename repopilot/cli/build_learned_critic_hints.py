from __future__ import annotations

import argparse
import json

from repopilot.critic.learned import load_jsonl, write_learned_failure_hints


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert learned critic predictions into RepoPilot critic-hints JSON."
    )
    parser.add_argument("predictions_jsonl", help="Prediction JSONL from predict_critic_lora.")
    parser.add_argument("--output-json", required=True, help="Failure hints JSON output.")
    parser.add_argument("--output-md", default=None, help="Optional Markdown report output.")
    parser.add_argument("--title", default="Learned Critic Hints")
    parser.add_argument(
        "--include-invalid",
        action="store_true",
        help="Include rows that failed schema validation.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rows = load_jsonl(args.predictions_jsonl)
    hints = write_learned_failure_hints(
        rows,
        args.output_json,
        output_md=args.output_md,
        title=args.title,
        include_invalid=args.include_invalid,
    )
    print(json.dumps({"hints": len(hints), "output_json": args.output_json}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
