# Validation Log

## 2026-06-13: Failure critic hints for remaining dev-10 hard cases

- Source trajectory: `data/trajectories/swebench_lite_dev10_after_rescue.jsonl`
- Hint artifacts: `docs/reports/swebench_lite_dev10_failure_hints.json`,
  `docs/reports/swebench_lite_dev10_failure_hints.md`
- Critic run: `docs/reports/swebench_lite_dev10_critic.md`
- Merged report: `docs/reports/swebench_lite_dev10_after_critic.md`
- Model: `deepseek-v4-flash`

Engineering changes made during this stage:

- Added a rule-based failure critic that distills unresolved trajectories into
  prompt-ready hints: failure type, baseline signal, last failure, focus files,
  suggested searches, next steps, and avoidance rules.
- Added `repopilot.cli.build_failure_hints` for JSON/Markdown critic artifacts.
- Added `--critic-hints-file` to `run_task` and `run_benchmark`.
- Injected critic hints into both the iterative tool-agent prompt and the
  non-tool patch-provider prompt.

Critic follow-up run:

```bash
python3 -m repopilot.cli.run_benchmark data/swebench/lite_dev_10.jsonl \
  --input-format swebench \
  --task-id sqlfluff__sqlfluff-1517 \
  --task-id marshmallow-code__marshmallow-1343 \
  --critic-hints-file docs/reports/swebench_lite_dev10_failure_hints.json \
  --provider deepseek-tools \
  --model deepseek-v4-flash \
  --reasoning-effort max \
  --temperature 1.0 \
  --api-timeout-sec 180 \
  --max-steps 24 \
  --max-test-runs 8 \
  --model-retries 1
```

Result:

| Task | Before Critic | After Critic | Main Change |
|---|---:|---:|---|
| `sqlfluff__sqlfluff-1517` | no | no | Still no patch. |
| `marshmallow-code__marshmallow-1343` | no | yes | Patched `schema.py` to skip field validators when nested load returns `None`, plus retained the `Mapping` compatibility fix. |

Aggregate after merging critic trajectories with the previous dev-10 run:
`9/10` resolved.

Generated reports:

- Markdown: `docs/reports/swebench_lite_dev10_after_critic.md`
- JSON: `docs/reports/swebench_lite_dev10_after_critic.json`

Local regression suite:

```bash
python3 -m unittest discover -s tests
```

Result: `65` tests passed.

## 2026-06-12: Hard-case rescue loop for SWE-bench Lite dev-10

- Source run: `docs/reports/swebench_lite_dev10_tools_envpin.json`
- Rescue task ids: `docs/reports/swebench_lite_dev10_unresolved_task_ids.txt`
- Plan: `docs/reports/swebench_lite_dev10_rescue_plan.md`
- Model: `deepseek-v4-flash`
- Rescue budget: `max_steps=24`, `max_test_runs=8`, `api_timeout_sec=180`,
  `model_retries=1`

Engineering changes made during this stage:

- Added `--task-id` and `--task-ids-file` to `run_benchmark` so failed subsets
  can be replayed directly.
- Added `repopilot.cli.plan_rescue` to extract unresolved cases from a benchmark
  report and render a hard-case rerun plan.
- Added configurable model-call retry support for the DeepSeek tool-agent.
- Changed tool execution failures, such as a model reading a misspelled path, to
  become observations instead of crashing the whole benchmark batch.

Rescue outcomes:

| Task | Previous Failure | Rescue Outcome | Main Change |
|---|---|---:|---|
| `sqlfluff__sqlfluff-1517` | `no_patch` | no | Still no patch after the larger budget. |
| `sqlfluff__sqlfluff-1763` | `no_patch` | yes | Added safe atomic replacement for linted file writes. |
| `marshmallow-code__marshmallow-1343` | `unresolved_patch` | no | Tool-error handling kept the batch alive, but no final patch was produced. |
| `pvlib__pvlib-python-1606` | `model_timeout` | yes | Guarded golden-section width when upper and lower bounds are equal. |

Aggregate after merging rescue trajectories with the original dev-10 run:
`8/10` resolved.

Generated reports:

- Markdown: `docs/reports/swebench_lite_dev10_after_rescue.md`
- JSON: `docs/reports/swebench_lite_dev10_after_rescue.json`

Local regression suite:

```bash
python3 -m unittest discover -s tests
```

Result: `59` tests passed.

## 2026-06-12: SWE-bench Lite 10-task tool-agent benchmark

- Tasks: first 10 records from the SWE-bench Lite dev split
- Repositories: `sqlfluff/sqlfluff`, `marshmallow-code/marshmallow`,
  `pvlib/pvlib-python`
- Model: `deepseek-v4-flash`
- Reasoning: `reasoning_effort=max`, `temperature=1.0`
- Environment: cached repository clones, per-task virtualenvs, editable
  installs, pytest verifier
- Setup command: `python -m pip install 'pytest<8' 'click<8.2' 'numpy<2' 'scipy<1.10' 'pandas<2' simplejson pytz pytest-mock pytest-timeout pytest-rerunfailures pytest-remotedata`

Environment calibration:

- Added shell quoting for SWE-bench pytest node ids.
- Relaxed incomplete parameterized pytest node ids to the containing function
  when SWE-bench Lite records are truncated at whitespace.
- Pinned `scipy<1.10` and `pandas<2` for pvlib tasks so the verifier reaches
  task-specific failures instead of dependency import errors.

Formal run:

```bash
python3 -m repopilot.cli.run_benchmark data/swebench/lite_dev_10.jsonl \
  --input-format swebench \
  --limit 10 \
  --repo-cache-dir data/repos \
  --use-venv \
  --install-repo \
  --setup-command "python -m pip install 'pytest<8' 'click<8.2' 'numpy<2' 'scipy<1.10' 'pandas<2' simplejson pytz pytest-mock pytest-timeout pytest-rerunfailures pytest-remotedata" \
  --provider deepseek-tools \
  --model deepseek-v4-flash \
  --reasoning-effort max \
  --temperature 1.0 \
  --api-timeout-sec 120 \
  --max-steps 16 \
  --max-test-runs 5 \
  --runs-dir runs_swebench_lite_dev10_tools_envpin \
  --trajectory-log data/trajectories/swebench_lite_dev10_tools_envpin.jsonl \
  --memory-store data/memory/swebench_lite_dev10_tools_envpin_memory.jsonl \
  --output data/benchmarks/swebench_lite_dev10_tools_envpin.json
```

Result:

| Task | Resolved | Failure Type | Changed Files |
|---|---:|---|---|
| `sqlfluff__sqlfluff-1625` | yes | `resolved` | `src/sqlfluff/rules/L031.py` |
| `sqlfluff__sqlfluff-2419` | yes | `resolved` | `src/sqlfluff/rules/L060.py` |
| `sqlfluff__sqlfluff-1733` | yes | `resolved` | `src/sqlfluff/rules/L039.py` |
| `sqlfluff__sqlfluff-1517` | no | `no_patch` | none |
| `sqlfluff__sqlfluff-1763` | no | `no_patch` | none |
| `marshmallow-code__marshmallow-1359` | yes | `resolved` | `src/marshmallow/fields.py` |
| `marshmallow-code__marshmallow-1343` | no | `unresolved_patch` | `src/marshmallow/marshalling.py` |
| `pvlib__pvlib-python-1707` | yes | `resolved` | `pvlib/iam.py` |
| `pvlib__pvlib-python-1072` | yes | `resolved` | `pvlib/temperature.py` |
| `pvlib__pvlib-python-1606` | no | `model_timeout` | none |

Aggregate: `6/10` resolved, average `12.1` model/tool steps per task,
average `3.0` verifier runs per task, and one model timeout.

Generated reports:

- Markdown: `docs/reports/swebench_lite_dev10_tools_envpin.md`
- JSON: `docs/reports/swebench_lite_dev10_tools_envpin.json`
- Environment checks: `docs/reports/swebench_lite_dev10_envcheck.md`,
  `docs/reports/swebench_lite_dev10_envfix.md`,
  `docs/reports/swebench_lite_dev10_pvlib_envpin.md`

Local regression suite:

```bash
python3 -m unittest discover -s tests
```

Result: `52` tests passed after adding the truncated-node-id regression test.

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
