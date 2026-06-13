# SWE-bench Lite Scale-30 Plan

## Scope

- Local task file: `data/swebench/lite_scale30.jsonl`
- Composition: first 23 rows from `dev` plus first 7 rows from `test`
- Total tasks: 30
- Unique task ids: 30

The `dev` split returned 23 rows from the Hugging Face rows API in this
environment, so scale-30 uses `dev23 + test7` instead of a non-existent
`dev30` file.

## Task Mix

| Repository | Tasks |
|---|---:|
| `astropy/astropy` | 6 |
| `sqlfluff/sqlfluff` | 5 |
| `pvlib/pvlib-python` | 5 |
| `pylint-dev/astroid` | 5 |
| `pydicom/pydicom` | 5 |
| `marshmallow-code/marshmallow` | 2 |
| `pyvista/pyvista` | 1 |
| `django/django` | 1 |

## Environment Readiness

| Shard | Tasks | Status | Evidence |
|---|---:|---|---|
| `dev12` calibrated shard | 12 | ready for DeepSeek run | `docs/reports/swebench_lite_dev12_env_smoke.md` |
| `test7` scale-out shard | 7 | blocked by environment/test-command setup | `docs/reports/swebench_lite_scale30_new7_env_smoke.md` |
| remaining `dev23` new repos | 11 | needs repo-specific setup pins | `astroid` smoke exposed pip/build setup failure |

## New-7 Smoke Result

The scale-30 supplement was run with the `scripted` provider, so no model calls
or patches were expected. The purpose was to verify preparation and baseline
execution.

| Failure Type | Tasks | Meaning |
|---|---:|---|
| `repo_install_error` | 6 | `astropy` tasks failed during editable install/build setup. |
| `test_command_error` | 1 | `django` prepared successfully, but the raw SWE-bench test selector is not a valid pytest path. |

## Next Actions

1. Run the already calibrated `dev12` shard with DeepSeek once
   `DEEPSEEK_API_KEY` is available in the shell.
2. Add repo-specific setup profiles for `astropy`, `astroid`, `pydicom`,
   `pyvista`, and `django`.
3. Re-run environment smoke by repo shard until setup failures are separated
   from agent failures.
4. Merge shard reports into a true scale-30 score report.
5. Apply rescue and failure critic only to tasks that reach baseline verifier
   execution.

## Candidate DeepSeek Command For Ready Shard

```bash
python3 -m repopilot.cli.run_benchmark data/swebench/lite_scale30.jsonl \
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
  --runs-dir runs_swebench_lite_scale30_dev12_tools \
  --trajectory-log data/trajectories/swebench_lite_scale30_dev12_tools.jsonl \
  --memory-store data/memory/swebench_lite_scale30_dev12_tools_memory.jsonl \
  --output data/benchmarks/swebench_lite_scale30_dev12_tools.json
```
