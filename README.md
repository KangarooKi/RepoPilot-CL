# RepoPilot-CL

RepoPilot-CL is a DeepSeek-V4-powered continual learning coding agent for repository-level issue repair. Instead of treating every bug report as an isolated task, it stores successful and failed repair trajectories, retrieves relevant past experience for new issues, and uses verifier feedback to select safer code patches.

The project is designed around four ideas:

1. Tool-use coding agent loops for search, read, edit, and test.
2. CI/test verifiers as the source of repair labels.
3. Trajectory memory for continual repository learning.
4. Patch-level reranking for best-of-N repair selection.

## Current MVP

This first implementation provides a local, testable skeleton:

- task schema and JSON loader
- sandbox runner with file setup, command execution, and git diff capture
- verifier result schema
- trajectory JSONL logger
- simple memory store and retrieval baseline
- scripted patch provider for a toy repair task
- iterative DeepSeek tool loop with JSON actions
- robust edit actions for exact text replacement and unified diff patches
- per-task virtualenv setup for repository benchmarks
- trajectory-to-memory distillation for continual learning
- automatic memory retrieval and memory upsert in task/benchmark CLIs
- rule-based patch reranking for best-of-N candidate selection
- repository context packing and context/no-context ablation
- robust patch application with hunk recounting, path repair, and patch previews
- experiment runner for baseline, context, memory, and reranker variants
- API call timeouts and trajectory logging for model-call failures
- model-call retries and tool-error observations for hard-case recovery
- rescue planner for rerunning unresolved benchmark cases
- failure critic hints distilled from unsuccessful trajectories
- prepare/setup failure capture for larger benchmark shards
- failure-type distribution in benchmark reports
- repo/task-level environment profiles for scale-out benchmark shards
- Django SWE-bench selector normalization for `tests/runtests.py`
- trajectory-to-training-data builder for critic and reranker experiments
- CLI entry point for running a task

The full roadmap targets SWE-bench Lite / Verified, SWE-Bench-CL, ContextBench, and a small SWE-CI proof of concept.

## Validated Result

Latest local benchmark: DeepSeek-V4-Flash tool-agent on a 10-task SWE-bench
Lite dev slice, followed by hard-case rescue and failure-critic hint injection.

| Split | Tasks | Model | Stage | Resolved | Report |
|---|---:|---|---|---:|---|
| SWE-bench Lite dev-10 | 10 | `deepseek-v4-flash` | initial tool-agent | 6/10 | [`swebench_lite_dev10_tools_envpin.md`](docs/reports/swebench_lite_dev10_tools_envpin.md) |
| SWE-bench Lite dev-10 | 10 | `deepseek-v4-flash` | after rescue | 8/10 | [`swebench_lite_dev10_after_rescue.md`](docs/reports/swebench_lite_dev10_after_rescue.md) |
| SWE-bench Lite dev-10 | 10 | `deepseek-v4-flash` | after failure critic | 9/10 | [`swebench_lite_dev10_after_critic.md`](docs/reports/swebench_lite_dev10_after_critic.md) |

The run uses cached upstream repositories, per-task virtualenvs, editable
installs, pytest verification, trajectory memory, and the JSON tool-action
loop. The subset covers `sqlfluff`, `marshmallow`, and `pvlib`; unresolved
cases are kept in the report with failure types so they can seed the next
debugging and continual-learning stage.

The next scale-up target is a 30-task SWE-bench Lite shard built as `dev23 +
test7`, because the Hugging Face rows API returned 23 rows for the Lite `dev`
split in this environment. The scale-30 plan is tracked in
[`swebench_lite_scale30_plan.md`](docs/reports/swebench_lite_scale30_plan.md);
the dev-23 environment notes remain in
[`swebench_lite_dev23_scale_plan.md`](docs/reports/swebench_lite_dev23_scale_plan.md).

## Quick Start

Run the toy task:

```bash
python3 -m repopilot.cli.run_task tasks/toy/divide_by_zero/task.json
```

Run the toy task with DeepSeek:

```bash
export DEEPSEEK_API_KEY="..."
python3 -m repopilot.cli.run_task tasks/toy/divide_by_zero/task.json --provider deepseek --model deepseek-v4-flash --reasoning-effort max --temperature 1.0
```

Run the toy task with the iterative DeepSeek tool loop:

```bash
export DEEPSEEK_API_KEY="..."
python3 -m repopilot.cli.run_task tasks/toy/divide_by_zero/task.json --provider deepseek-tools --model deepseek-v4-flash --reasoning-effort max --temperature 1.0
```

If your local Python runtime does not trust the system certificate chain, pass
`--ca-bundle /path/to/cacert.pem`. For one-off local debugging only, the CLI also
supports `--allow-insecure-ssl`.

The iterative loop asks the model to emit one JSON action per turn:

```json
{"action": "read_file", "args": {"path": "calc.py", "start": 1, "end": 80}, "thought": "Inspect the buggy function."}
```

Supported actions are `search_code`, `read_file`, `replace_text`,
`apply_patch`, `run_tests`, `get_diff`, and `submit`.

Run unit tests:

```bash
python3 -m unittest discover -s tests
```

Run with continual-learning memory:

```bash
python3 -m repopilot.cli.run_task tasks/toy/divide_by_zero/task.json \
  --memory-store data/memory/repopilot_memory.jsonl
```

By default, task and benchmark runs retrieve from the JSONL memory store before
repair and upsert a compact memory record after the trajectory finishes. Use
`--no-memory` to disable this loop for ablations.

Run DeepSeek best-of-N patch selection:

```bash
python3 -m repopilot.cli.run_task tasks/toy/divide_by_zero/task.json \
  --provider deepseek \
  --num-candidates 3 \
  --reranker rule
```

The current reranker is a lightweight baseline. It scores candidate patches by
patch size, hard-coded assertion risk, issue/error overlap, and retrieved memory
overlap, then verifies candidates in ranked order.

For repository tasks, the non-tool DeepSeek provider builds a compact context
pack before asking for candidate patches. The context pack searches the prepared
repository with terms from the issue, test command, benchmark test names, and
retrieved memories, then includes a small set of line-numbered snippets:

```bash
python3 -m repopilot.cli.run_benchmark data/swebench/lite_dev_5.jsonl \
  --input-format swebench \
  --limit 1 \
  --provider deepseek \
  --num-candidates 3 \
  --reranker rule \
  --context-max-snippets 8 \
  --context-lines 16
```

Use `--no-context` when you want a pure prompt-only baseline for ablation.

Run a task suite:

```bash
python3 -m repopilot.cli.run_benchmark "tasks/toy/*/task.json" --provider deepseek-tools
```

Run an ablation experiment:

```bash
python3 -m repopilot.cli.run_experiment "tasks/toy/*/task.json" \
  --provider scripted \
  --output-dir data/experiments/toy_ablation
```

This runs `baseline`, `context`, `memory`, and `memory_reranker` variants with
isolated artifacts, then writes `experiment_summary.json` and `report.md`.

The default experiment variants are:

| Variant | Context | Memory | Reranker |
|---|---:|---:|---|
| `baseline` | off | off | none |
| `context` | on | off | none |
| `memory` | on | on | none |
| `memory_reranker` | on | on | rule-based best-of-N |

Build reranker training data from trajectories:

```bash
python3 -m repopilot.cli.build_reranker_dataset \
  data/experiments/toy_ablation/memory_reranker/trajectory.jsonl \
  --output data/reranker/reranker_examples.jsonl
```

Each verified candidate patch becomes one JSONL example with the issue, baseline
failure, retrieved memory ids, candidate patch, trajectory summary, and verifier
label.

Build critic/reranker training examples from full agent trajectories:

```bash
python3 -m repopilot.cli.build_training_dataset \
  data/trajectories/swebench_lite_scale30_non_astropy_tools_after_rescue.jsonl \
  --output-jsonl docs/reports/swebench_lite_scale30_non_astropy_training_examples.jsonl \
  --output-summary-json docs/reports/swebench_lite_scale30_non_astropy_training_dataset_summary.json \
  --output-summary-md docs/reports/swebench_lite_scale30_non_astropy_training_dataset_summary.md \
  --title "SWE-bench Lite Scale-30 Non-Astropy Training Dataset Summary"
```

The critic objective learns from the issue, baseline signal, final verifier
signal, and action trace to predict failure type, focus files, searches, and
next-step hints. The reranker objective learns from issue/test signal plus a
candidate patch to predict whether the patch resolved the task. Empty final
patches are skipped for reranker examples by default.

Train and use the lightweight learned reranker:

```bash
python3 -m repopilot.cli.train_reranker \
  data/reranker/reranker_examples.jsonl \
  --model-output data/reranker/reranker_model.json

python3 -m repopilot.cli.run_task tasks/toy/divide_by_zero/task.json \
  --provider deepseek \
  --num-candidates 3 \
  --reranker learned \
  --reranker-model data/reranker/reranker_model.json
```

Run a SWE-bench-style JSONL subset:

```bash
python3 -m repopilot.cli.run_benchmark swebench_lite_subset.jsonl --input-format swebench --limit 5 --provider deepseek-tools
```

RepoPilot expects SWE-bench-style records with fields such as `instance_id`,
`repo`, `base_commit`, `problem_statement`, `FAIL_TO_PASS`, and `PASS_TO_PASS`.
For local dry runs, records may also provide `local_repo_path` and
`test_command`.

Download and inspect a SWE-bench Lite subset:

```bash
python3 -m repopilot.cli.download_swebench --split dev --length 5 --output data/swebench/lite_dev_5.jsonl
python3 -m repopilot.cli.inspect_tasks data/swebench/lite_dev_5.jsonl --input-format swebench
```

For real SWE-bench dry runs, cache GitHub repositories and provide a setup
command when needed:

```bash
python3 -m repopilot.cli.run_benchmark data/swebench/lite_dev_5.jsonl \
  --input-format swebench \
  --limit 1 \
  --max-pass-to-pass 0 \
  --repo-cache-dir data/repos \
  --use-venv \
  --install-repo \
  --setup-command "python -m pip install 'click<8.2' pytest" \
  --provider deepseek-tools \
  --api-timeout-sec 120
```

For larger mixed-repository shards, add `--env-profiles-file` to apply
repo/task-specific setup overrides, for example
`configs/swebench_lite_scale30_env_profiles.json`.

Render a benchmark report from a summary and trajectory log:

```bash
python3 -m repopilot.cli.report_benchmark \
  --summary data/benchmarks/swebench_lite_dev3_tools_envfix.json \
  --trajectory data/trajectories/swebench_lite_dev3_tools_envfix.jsonl \
  --output-md docs/reports/swebench_lite_dev3_tools_envfix.md \
  --output-json docs/reports/swebench_lite_dev3_tools_envfix.json \
  --title "SWE-bench Lite Dev-3 Tool-Agent Report"
```

Merge shard reports and rescue reports into a canonical final report:

```bash
python3 -m repopilot.cli.merge_benchmark_reports \
  docs/reports/swebench_lite_scale30_non_astropy_tools_merged.json \
  docs/reports/swebench_lite_scale30_non_astropy_rescue.json \
  docs/reports/swebench_lite_scale30_non_astropy_rescue_remaining4.json \
  --task-ids-file docs/reports/swebench_lite_scale30_non_astropy_task_ids.txt \
  --require-task-count 24 \
  --output-md docs/reports/swebench_lite_scale30_non_astropy_tools_after_rescue.md \
  --output-json docs/reports/swebench_lite_scale30_non_astropy_tools_after_rescue.json \
  --title "SWE-bench Lite Scale-30 Non-Astropy DeepSeek Tools After Rescue"
```

When the same task appears in multiple reports, the merge keeps a resolved
trajectory over an unresolved one; if both have the same resolved status, the
later report wins. This makes hard-case rescue runs reproducible without
hand-written merge scripts.

Compare two benchmark reports to quantify gains and regressions:

```bash
python3 -m repopilot.cli.compare_benchmark_reports \
  --base docs/reports/swebench_lite_scale30_non_astropy_tools_merged.json \
  --candidate docs/reports/swebench_lite_scale30_non_astropy_tools_after_rescue.json \
  --base-name initial \
  --candidate-name after_rescue \
  --task-ids-file docs/reports/swebench_lite_scale30_non_astropy_task_ids.txt \
  --require-same-tasks \
  --output-md docs/reports/swebench_lite_scale30_non_astropy_rescue_comparison.md \
  --output-json docs/reports/swebench_lite_scale30_non_astropy_rescue_comparison.json \
  --title "SWE-bench Lite Scale-30 Non-Astropy Rescue Comparison"
```

The comparison report lists gained, lost, still-resolved, and still-unresolved
tasks, plus failure-type transitions such as `model_timeout -> resolved`.

Summarize multiple benchmark reports into an ablation-style suite table:

```bash
python3 -m repopilot.cli.summarize_benchmark_suite \
  --report initial=docs/reports/swebench_lite_scale30_non_astropy_tools_merged.json \
  --report after_rescue=docs/reports/swebench_lite_scale30_non_astropy_tools_after_rescue.json \
  --baseline initial \
  --require-same-tasks \
  --output-md docs/reports/swebench_lite_scale30_non_astropy_suite_summary.md \
  --output-json docs/reports/swebench_lite_scale30_non_astropy_suite_summary.json \
  --title "SWE-bench Lite Scale-30 Non-Astropy Suite Summary"
```

The suite summary is intended for larger ablations, for example baseline vs.
memory vs. critic rescue vs. reranker runs, and includes per-repository
breakdowns for each variant.

Write a reproducibility manifest for a benchmark result:

```bash
python3 -m repopilot.cli.write_run_manifest \
  --name "SWE-bench Lite Scale-30 Non-Astropy After Rescue" \
  --command "python3 -m repopilot.cli.merge_benchmark_reports ..." \
  --dataset data/swebench/lite_scale30.jsonl \
  --task-ids-file docs/reports/swebench_lite_scale30_non_astropy_task_ids.txt \
  --provider deepseek-tools \
  --model deepseek-v4-flash \
  --report-json docs/reports/swebench_lite_scale30_non_astropy_tools_after_rescue.json \
  --artifact env_profiles=configs/swebench_lite_scale30_env_profiles.json \
  --artifact suite_summary=docs/reports/swebench_lite_scale30_non_astropy_suite_summary.json \
  --output-md docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.md \
  --output-json docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json
```

The manifest records metrics, git commit, model/provider, command, notes, and
SHA256 hashes for the dataset and report artifacts. API keys should remain in
environment variables and are not written into manifests.

Validate benchmark artifacts before publishing a result:

```bash
python3 -m repopilot.cli.validate_benchmark_artifacts \
  --report docs/reports/swebench_lite_scale30_non_astropy_tools_after_rescue.json \
  --comparison docs/reports/swebench_lite_scale30_non_astropy_rescue_comparison.json \
  --suite docs/reports/swebench_lite_scale30_non_astropy_suite_summary.json \
  --manifest docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json \
  --output-md docs/reports/swebench_lite_scale30_non_astropy_artifact_validation.md \
  --output-json docs/reports/swebench_lite_scale30_non_astropy_artifact_validation.json \
  --title "SWE-bench Lite Scale-30 Non-Astropy Artifact Validation"
```

The validator recomputes report metrics, comparison transitions, suite
breakdowns, manifest metrics, and artifact hashes; it exits nonzero if any check
fails.

Create a hard-case rescue plan from unresolved benchmark cases:

```bash
python3 -m repopilot.cli.plan_rescue \
  --report docs/reports/swebench_lite_dev10_tools_envpin.json \
  --output-task-ids docs/reports/swebench_lite_dev10_unresolved_task_ids.txt \
  --output-md docs/reports/swebench_lite_dev10_rescue_plan.md
```

Then rerun only those unresolved task ids with a larger step/test budget,
model-call retries, and the same environment pins.

Build failure critic hints from unresolved trajectories:

```bash
python3 -m repopilot.cli.build_failure_hints \
  data/trajectories/swebench_lite_dev10_after_rescue.jsonl \
  --output-json docs/reports/swebench_lite_dev10_failure_hints.json \
  --output-md docs/reports/swebench_lite_dev10_failure_hints.md
```

Pass those hints into a follow-up run with `--critic-hints-file`.

## Model Plan

| Component | Planned Model |
|---|---|
| Main coding actor | DeepSeek-V4-Flash |
| Hard-task teacher | DeepSeek-V4-Pro |
| Public critic baseline | OpenHands Critic 4B |
| Code localization | OpenHands CodeScout-4B |
| Self-trained reranker | RepoPilot-Reranker |

## Benchmark Plan

| Benchmark | Purpose |
|---|---|
| SWE-bench Lite / Verified | Base issue repair ability |
| SWE-Bench-CL | Continual learning, transfer, forgetting |
| ContextBench | Memory retrieval quality |
| SWE-CI | Long-term CI maintainability and regression |
