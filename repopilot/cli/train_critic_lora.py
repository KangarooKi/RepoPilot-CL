from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class TokenizedExample:
    input_ids: list[int]
    labels: list[int]
    attention_mask: list[int]


class CriticSFTDataset:
    def __init__(
        self,
        path: str | Path,
        *,
        tokenizer: Any,
        max_seq_length: int,
        max_examples: int | None = None,
    ) -> None:
        self.path = str(path)
        self.tokenizer = tokenizer
        self.max_seq_length = max_seq_length
        self.rows = _load_rows(path, max_examples=max_examples)

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict[str, list[int]]:
        example = _tokenize_row(
            self.rows[index],
            tokenizer=self.tokenizer,
            max_seq_length=self.max_seq_length,
        )
        return {
            "input_ids": example.input_ids,
            "labels": example.labels,
            "attention_mask": example.attention_mask,
        }


class CausalLMCollator:
    def __init__(self, *, tokenizer: Any, pad_to_multiple_of: int = 8) -> None:
        self.tokenizer = tokenizer
        self.pad_to_multiple_of = pad_to_multiple_of

    def __call__(self, features: list[dict[str, list[int]]]) -> dict[str, Any]:
        import torch

        max_len = max(len(item["input_ids"]) for item in features)
        if self.pad_to_multiple_of:
            remainder = max_len % self.pad_to_multiple_of
            if remainder:
                max_len += self.pad_to_multiple_of - remainder
        pad_id = self.tokenizer.pad_token_id
        batch_input_ids = []
        batch_attention_mask = []
        batch_labels = []
        for item in features:
            pad_len = max_len - len(item["input_ids"])
            batch_input_ids.append(item["input_ids"] + [pad_id] * pad_len)
            batch_attention_mask.append(item["attention_mask"] + [0] * pad_len)
            batch_labels.append(item["labels"] + [-100] * pad_len)
        return {
            "input_ids": torch.tensor(batch_input_ids, dtype=torch.long),
            "attention_mask": torch.tensor(batch_attention_mask, dtype=torch.long),
            "labels": torch.tensor(batch_labels, dtype=torch.long),
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train the RepoPilot Test-Time-Critic LoRA adapter with TensorBoard logs."
    )
    parser.add_argument("config", help="Training YAML config path.")
    parser.add_argument(
        "--stage",
        choices=["warmstart", "adaptation"],
        default="warmstart",
        help="Dataset stage to train on.",
    )
    parser.add_argument("--train-file", default=None, help="Override train JSONL.")
    parser.add_argument("--eval-file", default=None, help="Override eval JSONL.")
    parser.add_argument("--output-dir", default=None, help="Override adapter output dir.")
    parser.add_argument(
        "--logging-dir",
        default=None,
        help="TensorBoard logging dir. Defaults to OUTPUT_DIR/runs.",
    )
    parser.add_argument(
        "--adapter-init",
        default=None,
        help="Optional existing LoRA adapter to continue training from.",
    )
    parser.add_argument("--max-train-examples", type=int, default=None)
    parser.add_argument("--max-eval-examples", type=int, default=None)
    parser.add_argument("--max-steps", type=int, default=None)
    parser.add_argument("--num-train-epochs", type=float, default=None)
    parser.add_argument("--learning-rate", type=float, default=None)
    parser.add_argument("--max-seq-length", type=int, default=None)
    parser.add_argument("--save-total-limit", type=int, default=2)
    parser.add_argument("--resume-from-checkpoint", default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only load/tokenize datasets and print resolved paths.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = _load_config(args.config)
    train_file = args.train_file or _stage_path(config, args.stage, "train")
    eval_file = args.eval_file or _stage_path(config, args.stage, "dev")
    base_output_dir = args.output_dir or str(config["output_dir"])
    output_dir = str(Path(base_output_dir) / args.stage)
    logging_dir = args.logging_dir or str(Path(output_dir) / "runs")
    training_config = dict(config.get("training", {}))
    lora_config = dict(config.get("lora", {}))
    max_seq_length = int(args.max_seq_length or training_config.get("max_seq_length", 8192))

    print(
        json.dumps(
            {
                "stage": args.stage,
                "base_model": config["base_model"],
                "train_file": train_file,
                "eval_file": eval_file,
                "output_dir": output_dir,
                "logging_dir": logging_dir,
                "max_seq_length": max_seq_length,
                "adapter_init": args.adapter_init,
            },
            indent=2,
        )
    )

    _assert_file(train_file, "train file")
    _assert_file(eval_file, "eval file")
    _assert_dir(config["base_model"], "base model")

    _require_training_deps()
    from peft import LoraConfig, PeftModel, get_peft_model
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments

    tokenizer = AutoTokenizer.from_pretrained(
        str(config["base_model"]),
        trust_remote_code=True,
        use_fast=True,
    )
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

    train_dataset = CriticSFTDataset(
        train_file,
        tokenizer=tokenizer,
        max_seq_length=max_seq_length,
        max_examples=args.max_train_examples,
    )
    eval_dataset = CriticSFTDataset(
        eval_file,
        tokenizer=tokenizer,
        max_seq_length=max_seq_length,
        max_examples=args.max_eval_examples,
    )
    print(f"Loaded train examples: {len(train_dataset)} from {train_file}")
    print(f"Loaded eval examples: {len(eval_dataset)} from {eval_file}")
    if args.dry_run:
        preview = train_dataset[0]
        trainable_tokens = sum(1 for value in preview["labels"] if value != -100)
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "preview_tokens": len(preview["input_ids"]),
                    "preview_trainable_tokens": trainable_tokens,
                },
                indent=2,
            )
        )
        return 0

    model = AutoModelForCausalLM.from_pretrained(
        str(config["base_model"]),
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
        device_map=None,
    )
    if training_config.get("gradient_checkpointing", True):
        model.config.use_cache = False
        model.gradient_checkpointing_enable()
        model.enable_input_require_grads()

    if args.adapter_init:
        _assert_dir(args.adapter_init, "adapter init")
        model = PeftModel.from_pretrained(model, args.adapter_init, is_trainable=True)
    else:
        peft_config = LoraConfig(
            r=int(lora_config.get("r", 32)),
            lora_alpha=int(lora_config.get("alpha", 64)),
            lora_dropout=float(lora_config.get("dropout", 0.05)),
            target_modules=list(lora_config.get("target_modules", [])),
            task_type="CAUSAL_LM",
        )
        model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    train_args_kwargs = {
        "output_dir": output_dir,
        "per_device_train_batch_size": int(
            training_config.get("per_device_train_batch_size", 1)
        ),
        "per_device_eval_batch_size": int(training_config.get("per_device_eval_batch_size", 1)),
        "gradient_accumulation_steps": int(
            training_config.get("gradient_accumulation_steps", 8)
        ),
        "learning_rate": float(args.learning_rate or training_config.get("learning_rate", 1e-4)),
        "num_train_epochs": float(
            args.num_train_epochs
            if args.num_train_epochs is not None
            else training_config.get("num_train_epochs", 1)
        ),
        "warmup_ratio": float(training_config.get("warmup_ratio", 0.03)),
        "weight_decay": float(training_config.get("weight_decay", 0.0)),
        "bf16": True,
        "gradient_checkpointing": bool(training_config.get("gradient_checkpointing", True)),
        "logging_steps": int(training_config.get("logging_steps", 10)),
        "eval_steps": int(training_config.get("eval_steps", 250)),
        "save_steps": int(training_config.get("save_steps", 500)),
        "save_total_limit": args.save_total_limit,
        "report_to": ["tensorboard"],
        "logging_dir": logging_dir,
        "remove_unused_columns": False,
        "dataloader_num_workers": 0,
        "optim": str(training_config.get("optim", "adamw_torch")),
    }
    if args.max_steps is not None:
        train_args_kwargs["max_steps"] = args.max_steps
    _set_eval_strategy(train_args_kwargs)
    train_args = TrainingArguments(**train_args_kwargs)

    trainer = Trainer(
        model=model,
        args=train_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=CausalLMCollator(tokenizer=tokenizer),
    )
    trainer.train(resume_from_checkpoint=args.resume_from_checkpoint)
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    metadata = {
        "config": args.config,
        "stage": args.stage,
        "base_model": str(config["base_model"]),
        "train_file": train_file,
        "eval_file": eval_file,
        "output_dir": output_dir,
        "logging_dir": logging_dir,
        "max_seq_length": max_seq_length,
        "adapter_init": args.adapter_init,
        "train_examples": len(train_dataset),
        "eval_examples": len(eval_dataset),
    }
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    Path(output_dir, "training_metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(metadata, indent=2))
    return 0


def _load_config(path: str | Path) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Training config must be a YAML mapping.")
    return payload


def _stage_path(config: dict[str, Any], stage: str, split: str) -> str:
    dataset = config.get("dataset", {})
    key = f"{stage}_{split}"
    if not isinstance(dataset, dict) or key not in dataset:
        raise SystemExit(f"Missing dataset.{key} in config.")
    return str(dataset[key])


def _assert_file(path: str | Path, label: str) -> None:
    if not Path(path).is_file():
        raise SystemExit(f"{label} does not exist: {path}")


def _assert_dir(path: str | Path, label: str) -> None:
    if not Path(path).is_dir():
        raise SystemExit(f"{label} does not exist: {path}")


def _require_training_deps() -> None:
    missing = []
    for module in ["torch", "transformers", "peft"]:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    if missing:
        raise SystemExit(
            "Missing training dependencies: "
            + ", ".join(missing)
            + ". Install torch, transformers, peft, and accelerate first."
        )


def _tokenize_row(
    row: dict[str, Any],
    *,
    tokenizer: Any,
    max_seq_length: int,
) -> TokenizedExample:
    messages = row.get("messages", [])
    if not isinstance(messages, list) or len(messages) < 3:
        raise ValueError("Each SFT row must contain system, user, and assistant messages.")
    prompt_messages = messages[:2]
    assistant_content = str(messages[2].get("content", ""))
    prompt_text = tokenizer.apply_chat_template(
        prompt_messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    completion_text = assistant_content + (tokenizer.eos_token or "")
    prompt_ids = tokenizer(prompt_text, add_special_tokens=False)["input_ids"]
    completion_ids = tokenizer(completion_text, add_special_tokens=False)["input_ids"]
    if len(completion_ids) >= max_seq_length:
        input_ids = completion_ids[-max_seq_length:]
        labels = input_ids.copy()
    else:
        max_prompt_len = max_seq_length - len(completion_ids)
        prompt_ids = prompt_ids[-max_prompt_len:]
        input_ids = prompt_ids + completion_ids
        labels = [-100] * len(prompt_ids) + completion_ids
    return TokenizedExample(
        input_ids=input_ids,
        labels=labels,
        attention_mask=[1] * len(input_ids),
    )


def _load_rows(path: str | Path, *, max_examples: int | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rows.append(json.loads(line))
            if max_examples is not None and len(rows) >= max_examples:
                break
    if not rows:
        raise ValueError(f"No rows loaded from {path}")
    return rows


def _set_eval_strategy(kwargs: dict[str, Any]) -> None:
    import inspect
    from transformers import TrainingArguments

    params = inspect.signature(TrainingArguments.__init__).parameters
    if "eval_strategy" in params:
        kwargs["eval_strategy"] = "steps"
    else:
        kwargs["evaluation_strategy"] = "steps"


if __name__ == "__main__":
    raise SystemExit(main())
