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
python3 -m repopilot.cli.run_task tasks/toy/divide_by_zero/task.json --provider deepseek --model deepseek-v4-flash --reasoning-effort max
```

Run unit tests:

```bash
python3 -m unittest discover -s tests
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
