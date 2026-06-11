from __future__ import annotations

import argparse
import json

from repopilot.benchmark.hf_datasets import HFDatasetRowsRequest, fetch_rows, write_jsonl


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download a SWE-bench dataset subset.")
    parser.add_argument(
        "--dataset",
        default="princeton-nlp/SWE-bench_Lite",
        help="Hugging Face dataset id.",
    )
    parser.add_argument("--config", default="default")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--length", type=int, default=5)
    parser.add_argument(
        "--output",
        default="data/swebench/lite_dev.jsonl",
        help="Output JSONL path.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    request = HFDatasetRowsRequest(
        dataset=args.dataset,
        config=args.config,
        split=args.split,
        offset=args.offset,
        length=args.length,
    )
    records = fetch_rows(request)
    output = write_jsonl(records, args.output)
    print(
        json.dumps(
            {
                "dataset": args.dataset,
                "split": args.split,
                "offset": args.offset,
                "length": args.length,
                "downloaded": len(records),
                "output": str(output),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

