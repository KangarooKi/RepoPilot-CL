from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from repopilot.critic.distill import CRITIC_SYSTEM_PROMPT
from repopilot.critic.learned import load_jsonl, parse_critic_output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a trained RepoPilot Test-Time-Critic LoRA adapter on SFT JSONL rows."
    )
    parser.add_argument("config", help="Training YAML config with base_model.")
    parser.add_argument("--input-jsonl", required=True, help="Critic SFT JSONL input.")
    parser.add_argument("--adapter", required=True, help="LoRA adapter directory.")
    parser.add_argument("--output-jsonl", required=True, help="Prediction JSONL output.")
    parser.add_argument("--base-model", default=None, help="Override base model path.")
    parser.add_argument("--max-examples", type=int, default=None)
    parser.add_argument("--max-input-tokens", type=int, default=8192)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument(
        "--device-map",
        default="auto",
        help="Transformers device_map value. Use 'none' to disable device_map.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = _load_config(args.config)
    base_model = args.base_model or str(config["base_model"])
    rows = load_jsonl(args.input_jsonl, max_examples=args.max_examples)
    if not rows:
        raise SystemExit(f"No rows loaded from {args.input_jsonl}")

    _assert_dir(base_model, "base model")
    _assert_dir(args.adapter, "adapter")
    _require_inference_deps()

    from peft import PeftModel
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True, use_fast=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

    device_map = None if args.device_map == "none" else args.device_map
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
        device_map=device_map,
    )
    model = PeftModel.from_pretrained(model, args.adapter)
    model.eval()

    output_path = Path(args.output_jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            prompt_messages = _prompt_messages(row)
            prompt_text = tokenizer.apply_chat_template(
                prompt_messages,
                tokenize=False,
                add_generation_prompt=True,
            )
            inputs = tokenizer(
                prompt_text,
                add_special_tokens=False,
                return_tensors="pt",
                truncation=True,
                max_length=args.max_input_tokens,
            )
            inputs = {key: value.to(_model_device(model)) for key, value in inputs.items()}
            generate_kwargs = {
                "max_new_tokens": args.max_new_tokens,
                "pad_token_id": tokenizer.pad_token_id,
                "eos_token_id": tokenizer.eos_token_id,
            }
            if args.temperature > 0:
                generate_kwargs["do_sample"] = True
                generate_kwargs["temperature"] = args.temperature
            else:
                generate_kwargs["do_sample"] = False
            with torch.no_grad():
                outputs = model.generate(**inputs, **generate_kwargs)
            completion_ids = outputs[0][inputs["input_ids"].shape[-1] :]
            raw_output = tokenizer.decode(completion_ids, skip_special_tokens=True).strip()
            parsed = parse_critic_output(raw_output)
            handle.write(
                json.dumps(
                    {
                        "example_id": row.get("example_id", ""),
                        "task_id": row.get("task_id", ""),
                        "repo": row.get("repo", ""),
                        "source_kind": row.get("source_kind", ""),
                        "valid_json": parsed.valid_json,
                        "schema_valid": parsed.schema_valid,
                        "parse_error": parsed.error,
                        "prediction": parsed.prediction,
                        "reference": row.get("target", {}),
                        "raw_output": raw_output,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    print(json.dumps({"examples": len(rows), "output_jsonl": str(output_path)}, indent=2))
    return 0


def _load_config(path: str | Path) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Training config must be a YAML mapping.")
    return payload


def _prompt_messages(row: dict[str, Any]) -> list[dict[str, str]]:
    messages = row.get("messages", [])
    if isinstance(messages, list) and len(messages) >= 2:
        return [
            {"role": str(item.get("role", "")), "content": str(item.get("content", ""))}
            for item in messages[:2]
            if isinstance(item, dict)
        ]
    input_text = str(row.get("input_text", ""))
    return [
        {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
        {"role": "user", "content": input_text},
    ]


def _model_device(model: Any) -> Any:
    return next(model.parameters()).device


def _assert_dir(path: str | Path, label: str) -> None:
    if not Path(path).is_dir():
        raise SystemExit(f"{label} does not exist: {path}")


def _require_inference_deps() -> None:
    missing = []
    for module in ["torch", "transformers", "peft"]:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    if missing:
        raise SystemExit(
            "Missing inference dependencies: "
            + ", ".join(missing)
            + ". Install torch, transformers, peft, and accelerate first."
        )


if __name__ == "__main__":
    raise SystemExit(main())
