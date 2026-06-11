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
- CLI entry point for running a task

The full roadmap targets SWE-bench Lite / Verified, SWE-Bench-CL, ContextBench, and a small SWE-CI proof of concept.

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

Supported actions are `search_code`, `read_file`, `apply_patch`, `run_tests`, `get_diff`, and `submit`.

Run unit tests:

```bash
python3 -m unittest discover -s tests
```

Run a task suite:

```bash
python3 -m repopilot.cli.run_benchmark "tasks/toy/*/task.json" --provider deepseek-tools
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
  --setup-command "python3 -m pip install pytest"
```

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
