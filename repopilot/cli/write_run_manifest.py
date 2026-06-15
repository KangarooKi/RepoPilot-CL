from __future__ import annotations

import argparse
import json
import subprocess

from repopilot.report.run_manifest import (
    build_run_manifest,
    write_run_manifest_artifacts,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Write a reproducibility manifest for a RepoPilot-CL benchmark run, "
            "including command, model, dataset, metrics, artifact hashes, and git commit."
        )
    )
    parser.add_argument("--name", required=True, help="Manifest/run display name.")
    parser.add_argument("--command", required=True, help="Command used to reproduce the run.")
    parser.add_argument("--dataset", required=True, help="Benchmark dataset path.")
    parser.add_argument("--task-ids-file", required=True, help="Task id file path.")
    parser.add_argument("--provider", required=True, help="Agent/provider name.")
    parser.add_argument("--model", required=True, help="Model name.")
    parser.add_argument("--report-json", required=True, help="Structured benchmark report JSON.")
    parser.add_argument(
        "--artifact",
        action="append",
        default=[],
        help="Extra artifact in LABEL=PATH form. Can be passed multiple times.",
    )
    parser.add_argument(
        "--note",
        action="append",
        default=[],
        help="Optional note to include in the manifest. Can be passed multiple times.",
    )
    parser.add_argument(
        "--git-commit",
        default=None,
        help="Git commit to record. Defaults to `git rev-parse HEAD`.",
    )
    parser.add_argument(
        "--created-at",
        default=None,
        help="Optional fixed UTC timestamp, useful for deterministic tests.",
    )
    parser.add_argument(
        "--output-md",
        default="data/reports/run_manifest.md",
        help="Markdown manifest output path.",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Optional structured manifest JSON output path.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = build_run_manifest(
        name=args.name,
        command=args.command,
        dataset=args.dataset,
        task_ids_file=args.task_ids_file,
        provider=args.provider,
        model=args.model,
        report_json=args.report_json,
        git_commit=args.git_commit or _git_commit(),
        artifacts=[_parse_artifact(value) for value in args.artifact],
        notes=list(args.note),
        created_at_utc=args.created_at,
    )
    write_run_manifest_artifacts(
        manifest,
        markdown_path=args.output_md,
        json_path=args.output_json,
    )
    print(json.dumps(manifest.to_dict(), indent=2))
    print(f"Markdown manifest: {args.output_md}")
    if args.output_json:
        print(f"JSON manifest: {args.output_json}")
    return 0


def _parse_artifact(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise SystemExit("--artifact must use LABEL=PATH form.")
    label, path = value.split("=", 1)
    label = label.strip()
    path = path.strip()
    if not label or not path:
        raise SystemExit("--artifact must use LABEL=PATH form.")
    return label, path


def _git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
