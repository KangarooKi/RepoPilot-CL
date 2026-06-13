# SWE-bench Lite Dev-23 Scale Plan

## Scope

- Dataset file: `data/swebench/lite_dev_23.jsonl`
- Source dataset: `princeton-nlp/SWE-bench_Lite`, split `dev`
- Requested rows: 30
- Returned rows: 23
- Goal: scale the validated dev-10 workflow to the full available Lite dev split in this environment.

## Task Mix

| Repository | Tasks |
|---|---:|
| `sqlfluff/sqlfluff` | 5 |
| `pvlib/pvlib-python` | 5 |
| `pylint-dev/astroid` | 5 |
| `pydicom/pydicom` | 5 |
| `marshmallow-code/marshmallow` | 2 |
| `pyvista/pyvista` | 1 |

| FAIL_TO_PASS Tests | Tasks |
|---:|---:|
| 1 | 18 |
| 2 | 1 |
| 3 | 3 |
| 5 | 1 |

| PASS_TO_PASS Bucket | Tasks |
|---|---:|
| `0` | 2 |
| `1-25` | 8 |
| `26-100` | 10 |
| `101+` | 3 |

## Environment Findings

The first dev-10 tasks use repositories already calibrated locally:

- `sqlfluff/sqlfluff`
- `marshmallow-code/marshmallow`
- `pvlib/pvlib-python`

The expanded dev-23 split adds:

- `pylint-dev/astroid`
- `pyvista/pyvista`
- `pydicom/pydicom`

An environment smoke run reached `pylint-dev/astroid` but failed during pip
dependency download from `files.pythonhosted.org` with a read timeout. This is
an environment/setup failure rather than an agent repair failure.

## New Evaluation Robustness

To make larger benchmark runs usable, `run_benchmark` now catches task
preparation failures and records them as normal unresolved trajectories instead
of crashing the whole batch.

Recorded failure types include:

- `setup_error`
- `repo_install_error`
- `test_patch_error`
- `prepare_error`

Benchmark reports now include a failure-type distribution table, so scaling runs
can separate agent failures from environment failures.

## Recommended Run Order

1. Re-run the calibrated first 10 tasks only when a fresh baseline is needed.
2. Run the two additional `pvlib` tasks to extend the calibrated slice to 12.
3. Run `astroid`, `pydicom`, and `pyvista` as separate repo shards after their
   setup commands are pinned.
4. Merge shard reports into a dev-23 report.
5. Apply rescue and failure critic loops only to agent failures, not setup
   failures.

## Candidate Commands

Calibrated first 12 tasks:

```bash
python3 -m repopilot.cli.run_benchmark data/swebench/lite_dev_23.jsonl \
  --input-format swebench \
  --limit 12 \
  --repo-cache-dir data/repos \
  --use-venv \
  --install-repo \
  --setup-command "python -m pip install 'pytest<8' 'click<8.2' 'numpy<2' 'scipy<1.10' 'pandas<2' simplejson pytz pytest-mock pytest-timeout pytest-rerunfailures pytest-remotedata" \
  --provider deepseek-tools \
  --model deepseek-v4-flash \
  --reasoning-effort max \
  --temperature 1.0 \
  --api-timeout-sec 180 \
  --max-steps 20 \
  --max-test-runs 6 \
  --model-retries 1 \
  --runs-dir runs_swebench_lite_dev12_tools \
  --trajectory-log data/trajectories/swebench_lite_dev12_tools.jsonl \
  --memory-store data/memory/swebench_lite_dev12_tools_memory.jsonl \
  --output data/benchmarks/swebench_lite_dev12_tools.json
```

Render a report:

```bash
python3 -m repopilot.cli.report_benchmark \
  --summary data/benchmarks/swebench_lite_dev12_tools.json \
  --trajectory data/trajectories/swebench_lite_dev12_tools.jsonl \
  --output-md docs/reports/swebench_lite_dev12_tools.md \
  --output-json docs/reports/swebench_lite_dev12_tools.json \
  --title "SWE-bench Lite Dev-12 Tool-Agent Report"
```
