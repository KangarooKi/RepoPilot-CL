# Rescue Plan

- Source report: `docs/reports/swebench_lite_scale30_non_astropy_tools_merged.json`
- Task id file: `docs/reports/swebench_lite_scale30_non_astropy_rescue_task_ids.txt`
- Unresolved tasks: `8`

## Failure Mix

| Failure Type | Count |
|---|---:|
| `model_call_error` | 1 |
| `model_timeout` | 3 |
| `no_patch` | 1 |
| `repo_install_error` | 1 |
| `unresolved_patch` | 2 |

## Cases

| Task | Repository | Failure Type | Changed Files | Issue |
|---|---|---|---|---|
| `sqlfluff__sqlfluff-1625` | `sqlfluff/sqlfluff` | `model_call_error` | none | TSQL - L031 incorrectly triggers "Avoid using aliases in join condition" when no join present |
| `sqlfluff__sqlfluff-2419` | `sqlfluff/sqlfluff` | `model_timeout` | none | Rule L060 could give a specific error message |
| `sqlfluff__sqlfluff-1733` | `sqlfluff/sqlfluff` | `repo_install_error` | none | Extra space when first field moved to new line in a WITH statement |
| `sqlfluff__sqlfluff-1517` | `sqlfluff/sqlfluff` | `model_timeout` | none | "Dropped elements in sequence matching" when doubled semicolon |
| `sqlfluff__sqlfluff-1763` | `sqlfluff/sqlfluff` | `no_patch` | none | dbt postgres fix command errors with UnicodeEncodeError and also wipes the .sql file |
| `marshmallow-code__marshmallow-1343` | `marshmallow-code/marshmallow` | `model_timeout` | none | [version 2.20.0] TypeError: 'NoneType' object is not subscriptable |
| `pylint-dev__astroid-1978` | `pylint-dev/astroid` | `unresolved_patch` | `astroid/raw_building.py` | Deprecation warnings from numpy |
| `pyvista__pyvista-4315` | `pyvista/pyvista` | `unresolved_patch` | `pyvista/core/grid.py` | Rectilinear grid does not allow Sequences as inputs |

## Recommended Rerun

```bash
python3 -m repopilot.cli.run_benchmark data/swebench/lite_scale30.jsonl \
  --input-format swebench \
  --task-ids-file docs/reports/swebench_lite_scale30_non_astropy_rescue_task_ids.txt \
  --repo-cache-dir data/repos \
  --use-venv \
  --install-repo \
  --setup-command 'python -m pip install '"'"'pytest<8'"'"' '"'"'click<8.2'"'"' '"'"'numpy<2'"'"' '"'"'scipy<1.10'"'"' '"'"'pandas<2'"'"' simplejson pytz pytest-mock pytest-timeout pytest-rerunfailures pytest-remotedata' \
  --provider deepseek-tools \
  --model deepseek-v4-flash \
  --reasoning-effort max \
  --temperature 1.0 \
  --api-timeout-sec 240 \
  --max-steps 24 \
  --max-test-runs 8 \
  --model-retries 2 \
  --runs-dir runs_swebench_lite_scale30_non_astropy_rescue \
  --trajectory-log data/trajectories/swebench_lite_scale30_non_astropy_rescue.jsonl \
  --memory-store data/memory/swebench_lite_scale30_non_astropy_rescue_memory.jsonl \
  --output data/benchmarks/swebench_lite_scale30_non_astropy_rescue.json
```
