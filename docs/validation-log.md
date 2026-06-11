# Validation Log

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
