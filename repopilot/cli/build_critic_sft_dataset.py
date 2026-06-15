from __future__ import annotations

import argparse
import json

from repopilot.critic.distill import (
    load_critic_sft_from_swebench,
    load_critic_sft_from_training_examples,
    load_task_ids,
    split_critic_sft_by_task,
    summarize_critic_sft,
    write_critic_sft_jsonl,
    write_critic_sft_splits,
    write_critic_sft_summary,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build RepoPilot Test-Time-Critic SFT messages from SWE-bench records "
            "and/or RepoPilot critic training examples."
        )
    )
    parser.add_argument(
        "--swebench-jsonl",
        action="append",
        default=[],
        help="SWE-bench-style JSONL file(s) for generic critic warm start.",
    )
    parser.add_argument(
        "--training-examples-jsonl",
        action="append",
        default=[],
        help="RepoPilot TrainingExample JSONL file(s); only objective=critic rows are used.",
    )
    parser.add_argument(
        "--exclude-task-ids-file",
        action="append",
        default=[],
        help="Task ids to exclude from SWE-bench warm-start data, useful for held-out eval sets.",
    )
    parser.add_argument(
        "--max-swebench-records",
        type=int,
        default=None,
        help="Optional cap for SWE-bench warm-start rows.",
    )
    parser.add_argument(
        "--max-training-examples",
        type=int,
        default=None,
        help="Optional cap for RepoPilot trajectory critic rows.",
    )
    parser.add_argument(
        "--output-jsonl",
        default="data/training/critic_sft/critic_sft.jsonl",
        help="Output SFT JSONL path.",
    )
    parser.add_argument(
        "--split-output-dir",
        default=None,
        help="Optional directory for task-level train/dev/test JSONL splits.",
    )
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.7,
        help="Task-level train split ratio when --split-output-dir is set.",
    )
    parser.add_argument(
        "--dev-ratio",
        type=float,
        default=0.15,
        help="Task-level dev split ratio when --split-output-dir is set.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=13,
        help="Deterministic split seed.",
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
        "--title",
        default="RepoPilot Test-Time-Critic SFT Dataset",
        help="Markdown summary title.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.swebench_jsonl and not args.training_examples_jsonl:
        raise SystemExit("Pass at least one --swebench-jsonl or --training-examples-jsonl.")

    excluded_task_ids: set[str] = set()
    for path in args.exclude_task_ids_file:
        excluded_task_ids.update(load_task_ids(path))

    examples = []
    if args.swebench_jsonl:
        examples.extend(
            load_critic_sft_from_swebench(
                args.swebench_jsonl,
                exclude_task_ids=excluded_task_ids,
                max_records=args.max_swebench_records,
            )
        )
    if args.training_examples_jsonl:
        examples.extend(
            load_critic_sft_from_training_examples(
                args.training_examples_jsonl,
                max_examples=args.max_training_examples,
            )
        )

    write_critic_sft_jsonl(examples, args.output_jsonl)
    splits = None
    if args.split_output_dir:
        splits = split_critic_sft_by_task(
            examples,
            train_ratio=args.train_ratio,
            dev_ratio=args.dev_ratio,
            seed=args.seed,
        )
        write_critic_sft_splits(splits, args.split_output_dir)

    summary = summarize_critic_sft(
        examples,
        output=args.output_jsonl,
        split_output_dir=args.split_output_dir,
        splits=splits,
    )
    write_critic_sft_summary(
        summary,
        output_json=args.output_summary_json,
        output_md=args.output_summary_md,
        title=args.title,
    )
    print(json.dumps(summary.to_dict(), indent=2, ensure_ascii=False))
    print(f"Critic SFT dataset: {args.output_jsonl}")
    if args.split_output_dir:
        print(f"Split output dir: {args.split_output_dir}")
    if args.output_summary_json:
        print(f"Summary JSON: {args.output_summary_json}")
    if args.output_summary_md:
        print(f"Summary Markdown: {args.output_summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
