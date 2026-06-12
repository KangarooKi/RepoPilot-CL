# Validation Log

## 2026-06-12: SWE-bench Lite 3-task tool-agent benchmark

- Tasks: `sqlfluff__sqlfluff-1625`, `sqlfluff__sqlfluff-2419`,
  `sqlfluff__sqlfluff-1733`
- Repository: `sqlfluff/sqlfluff`
- Model: `deepseek-v4-flash`
- Reasoning: `reasoning_effort=max`, `temperature=1.0`
- Environment: cached repository clone, per-task virtualenv, editable install,
  pytest verifier

Initial run:

```bash
python3 -m repopilot.cli.run_benchmark data/swebench/lite_dev_3.jsonl \
  --input-format swebench \
  --limit 3 \
  --repo-cache-dir data/repos \
  --use-venv \
  --install-repo \
  --setup-command "python -m pip install pytest" \
  --provider deepseek-tools \
  --api-timeout-sec 60 \
  --max-steps 14 \
  --max-test-runs 4
```

Result: `1/3` resolved. Failure analysis showed that `sqlfluff__sqlfluff-1625`
was polluted by a Click API compatibility issue, so the agent patched the test
helper instead of the product code. `sqlfluff__sqlfluff-1733` was stopped by the
new API-call timeout and recorded a `model_call_error`, which kept the batch
from hanging.

Environment-corrected run:

```bash
python3 -m repopilot.cli.run_benchmark data/swebench/lite_dev_3.jsonl \
  --input-format swebench \
  --limit 3 \
  --repo-cache-dir data/repos \
  --use-venv \
  --install-repo \
  --setup-command "python -m pip install 'click<8.2' pytest" \
  --provider deepseek-tools \
  --api-timeout-sec 120 \
  --max-steps 16 \
  --max-test-runs 5
```

Result:

| Task | Resolved | Patch Lines | Main Change |
|---|---:|---:|---|
| `sqlfluff__sqlfluff-1625` | yes | 13 | Updated L031 description text to match the expected CLI output. |
| `sqlfluff__sqlfluff-2419` | yes | 14 | Added an L060 `LintResult` description based on `context.segment.raw_upper`. |
| `sqlfluff__sqlfluff-1733` | yes | 13 | Fixed L039 whitespace state handling so indentation whitespace is not treated as spacing between tokens. |

Aggregate: `3/3` resolved.

Generated reports:

- Markdown: `docs/reports/swebench_lite_dev3_tools_envfix.md`
- JSON: `docs/reports/swebench_lite_dev3_tools_envfix.json`

Engineering changes made during this stage:

- Added `--api-timeout-sec` to task, benchmark, and experiment CLIs.
- Added an end-to-end DeepSeek request deadline around response reading.
- Recorded `model_call_error` in tool-agent trajectories instead of crashing or
  hanging a batch.
- Recorded `propose_patch_error` for non-tool patch provider failures.
- Added `repopilot.cli.report_benchmark` for Markdown/JSON benchmark reports.

Local regression suite:

```bash
python3 -m unittest discover -s tests
```

Result: `48` tests passed.

## 2026-06-11: Context ablation and patch robustness

- Task: `sqlfluff__sqlfluff-2419`
- Repository: `sqlfluff/sqlfluff`
- Model: `deepseek-v4-flash`
- Reasoning: `reasoning_effort=max`, `temperature=1.0`
- Environment: cached repository clone, per-task virtualenv, editable install, pytest verifier

Non-tool best-of-N ablation:

```bash
python3 -m repopilot.cli.run_experiment data/swebench/lite_dev_3.jsonl \
  --input-format swebench \
  --limit 1 \
  --max-pass-to-pass 0 \
  --repo-cache-dir data/repos \
  --use-venv \
  --install-repo \
  --setup-command "python -m pip install pytest" \
  --provider deepseek \
  --num-candidates 2 \
  --output-dir data/experiments/swebench_lite_sqlfluff_2419_ablation_v2
```

Result:

| Variant | Context | Memory | Reranker | N | Resolved | Total |
|---|---:|---:|---|---:|---:|---:|
| `baseline` | off | off | none | 1 | 0 | 1 |
| `context` | on | off | none | 1 | 0 | 1 |
| `memory` | on | on | none | 1 | 0 | 1 |
| `memory_reranker` | on | on | rule | 2 | 0 | 1 |

Observed failure mode: the non-tool provider generated plausible but stale
patches that referenced old code structure. The runner now records candidate
patch previews in trajectories and applies generated diffs with hunk recounting
and unique-path repair, which makes these failures inspectable instead of
opaque.

Tool-agent baseline:

```bash
python3 -m repopilot.cli.run_benchmark data/swebench/lite_dev_3.jsonl \
  --input-format swebench \
  --limit 1 \
  --max-pass-to-pass 0 \
  --repo-cache-dir data/repos \
  --use-venv \
  --install-repo \
  --setup-command "python -m pip install pytest" \
  --provider deepseek-tools \
  --max-steps 12 \
  --max-test-runs 4 \
  --output data/benchmarks/swebench_lite_sqlfluff_2419_tools_v2.json
```

Result: `1/1` resolved, `14` patch lines.

Trajectory summary:

1. Baseline verifier reproduced the failing L060 description assertion.
2. The agent searched for `class Rule_L060` and read `src/sqlfluff/rules/L060.py`.
3. It replaced the generic `LintResult(context.segment, [fix])` with a
   `LintResult` carrying a description based on `context.segment.raw_upper`.
4. It checked the `LintResult` constructor, ran the target pytest, got a pass,
   retrieved the final diff, and submitted.

Local regression suite:

```bash
python3 -m unittest discover -s tests
```

Result: `46` tests passed.

## 2026-06-11: SWE-bench Lite single-task smoke

- Task: `sqlfluff__sqlfluff-2419`
- Repository: `sqlfluff/sqlfluff`
- Model: `deepseek-v4-flash`
- Reasoning: `reasoning_effort=max`, `temperature=1.0`
- Environment: cached repository clone, per-task virtualenv, editable install, pytest verifier
- Result: `1/1` resolved, `14` patch lines

Trajectory summary:

1. Baseline verifier reproduced the failing L060 description assertion.
2. The agent searched for `L060`, read the rule implementation, and inspected `LintResult`.
3. It changed the rule to emit a description based on `context.segment.raw_upper`.
4. The target pytest passed and the agent submitted the final diff.

Local regression suite:

```bash
python3 -m unittest discover -s tests
```

Result: `24` tests passed.
