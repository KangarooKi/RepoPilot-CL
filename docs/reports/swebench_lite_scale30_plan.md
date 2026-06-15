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
| non-Astropy scale-30 shard | 24 | ready for DeepSeek run | `docs/reports/swebench_lite_scale30_non_astropy_env_smoke.md`, `docs/reports/swebench_lite_scale30_non_astropy_env_retry.md`, `docs/reports/swebench_lite_scale30_pyvista_envprofile.md` |
| Astropy scale-30 shard | 6 | blocked by local macOS native bundled cfitsio/zlib build | `docs/reports/swebench_lite_scale30_astropy_envprofile.md` |

## New-7 Smoke Result

The scale-30 supplement was run with the `scripted` provider, so no model calls
or patches were expected. The purpose was to verify preparation and baseline
execution.

| Failure Type | Tasks | Meaning |
|---|---:|---|
| `repo_install_error` | 6 | `astropy` tasks failed during editable install/build setup. |
| `test_command_error` | 1 | `django` prepared successfully, but the raw SWE-bench test selector is not a valid pytest path. |

## Environment Profile Update

This stage added declaration-based environment profiles:
`configs/swebench_lite_scale30_env_profiles.json`. `run_benchmark` now accepts
`--env-profiles-file`, and each profile can override `setup_command`,
`test_command`, and `install_repo` at repo or task granularity.

Django is now handled in the SWE-bench loader rather than by a profile. Selectors
like `test_override_file_upload_permissions (test_utils.tests.OverrideSettingsTests)`
are converted to:

```bash
python3 tests/runtests.py test_utils.tests.OverrideSettingsTests.test_override_file_upload_permissions
```

Validation smoke:

| Task | Before | After |
|---|---|---|
| `django__django-10914` | `test_command_error` | reaches baseline verifier; scripted run is `no_patch` |
| `astropy__astropy-14182` | `repo_install_error` from missing `setuptools.dep_util` | setup now reaches native bundled cfitsio/zlib build; blocked by local macOS compiler error |

Astropy still needs either a Linux/containerized runner, a repo-specific system
library build profile, or a task-level strategy that builds only the required
extensions.

## Non-Astropy Scale-30 Smoke

The non-Astropy shard is tracked in
`docs/reports/swebench_lite_scale30_non_astropy_task_ids.txt` and contains 24
tasks from `sqlfluff`, `marshmallow`, `pvlib`, `astroid`, `pyvista`, `pydicom`,
and `django`.

The first full smoke used the `scripted` provider with no model calls. It reached
baseline verifier execution on 22/24 tasks. The remaining two were transient
`git clone` preparation failures for `pyvista__pyvista-4315` and
`pydicom__pydicom-1694`.

Retry result:

| Task | Retry Outcome | Meaning |
|---|---|---|
| `pydicom__pydicom-1694` | `no_patch`, `test_runs=1` | Environment is ready; scripted no-patch failure is expected. |
| `pyvista__pyvista-4315` | `repo_install_error`, `test_runs=0` | Clone succeeds, but pip dependency download from `files.pythonhosted.org` times out during editable install. |

A follow-up PyVista environment profile disables the default editable install
and runs `pip install --timeout 180 --retries 10 --prefer-binary -e .` inside
`setup_command`. With that profile, `pyvista__pyvista-4315` reaches baseline
verifier execution (`no_patch`, `test_runs=1`).

Current non-Astropy readiness: 24/24 tasks reach the baseline verifier. These
tasks are ready for a DeepSeek score run.

## Non-Astropy DeepSeek Tools Score

The first formal non-Astropy run used `deepseek-v4-flash` with tool actions,
`reasoning_effort=max`, `temperature=1.0`, `max_steps=20`, `max_test_runs=6`,
and `model_retries=1`.

The run was split into smaller shards to avoid losing completed trajectories
when PyVista dependency setup was slow. The final merged report is deduplicated
by task id and ordered by
`docs/reports/swebench_lite_scale30_non_astropy_task_ids.txt`.

Report:
`docs/reports/swebench_lite_scale30_non_astropy_tools_merged.md`

Overall result:

| Metric | Value |
|---|---:|
| Tasks | 24 |
| Resolved | 16 |
| Resolved rate | 0.667 |

Repository breakdown:

| Repository | Resolved / Tasks |
|---|---:|
| `pvlib/pvlib-python` | 5 / 5 |
| `pydicom/pydicom` | 5 / 5 |
| `pylint-dev/astroid` | 4 / 5 |
| `django/django` | 1 / 1 |
| `marshmallow-code/marshmallow` | 1 / 2 |
| `pyvista/pyvista` | 0 / 1 |
| `sqlfluff/sqlfluff` | 0 / 5 |

Unresolved failure types:

| Failure Type | Tasks |
|---|---:|
| `model_timeout` | 3 |
| `unresolved_patch` | 2 |
| `model_call_error` | 1 |
| `repo_install_error` | 1 |
| `no_patch` | 1 |

## Non-Astropy Failure-Critic Rescue

The next stage turned the 8 unresolved non-Astropy cases into explicit rescue
inputs:

- Rescue task list:
  `docs/reports/swebench_lite_scale30_non_astropy_rescue_task_ids.txt`
- Rescue plan:
  `docs/reports/swebench_lite_scale30_non_astropy_rescue_plan.md`
- Failure hints:
  `docs/reports/swebench_lite_scale30_non_astropy_failure_hints.md`

The rescue runs reused `deepseek-v4-flash` with `deepseek-tools`,
`reasoning_effort=max`, `temperature=1.0`, a higher API timeout, a larger step
budget, and critic hints extracted from the previous trajectories.

Rescue result:

| Stage | Resolved / Tasks | Notes |
|---|---:|---|
| Initial non-Astropy score | 16 / 24 | Formal merged DeepSeek tools run. |
| First rescue shard | 3 / 3 | Recovered three SQLFluff cases before the interrupted SQLFluff timeout case. |
| Remaining rescue shard | 3 / 4 | Recovered SQLFluff, Marshmallow, and Astroid; PyVista remained unresolved. |
| Final merged score after rescue | 22 / 24 | Deduplicated by task id, preferring resolved rescue trajectories. |

Report:
`docs/reports/swebench_lite_scale30_non_astropy_tools_after_rescue.md`

Comparison:
`docs/reports/swebench_lite_scale30_non_astropy_rescue_comparison.md`

Suite summary:
`docs/reports/swebench_lite_scale30_non_astropy_suite_summary.md`

After-rescue repository breakdown:

| Repository | Resolved / Tasks |
|---|---:|
| `sqlfluff/sqlfluff` | 4 / 5 |
| `marshmallow-code/marshmallow` | 2 / 2 |
| `pvlib/pvlib-python` | 5 / 5 |
| `pylint-dev/astroid` | 5 / 5 |
| `pyvista/pyvista` | 0 / 1 |
| `pydicom/pydicom` | 5 / 5 |
| `django/django` | 1 / 1 |

Remaining unresolved cases:

| Task | Failure Type | Note |
|---|---|---|
| `sqlfluff__sqlfluff-1517` | `model_timeout` | Rescue attempt was interrupted while waiting for a model response; no successful rescue trajectory was recorded. |
| `pyvista__pyvista-4315` | `unresolved_patch` | Environment reaches verifier, but the generated patch still fails the target behavior. |

## Next Actions

1. Run a focused single-task rescue for `sqlfluff__sqlfluff-1517`, using the
   existing failure hint but a tighter prompt and/or lower response latency
   settings so the model response does not stall again.
2. Diagnose `pyvista__pyvista-4315` at the patch-quality level: compare the
   failing verifier output with `pyvista/core/grid.py` and the relevant grid
   tests before rerunning the model.
3. Keep the 6 Astropy tasks as a separate Linux/container or native-build
   follow-up shard.
4. Once those two hard non-Astropy cases are handled, publish a final scale-30
   table that separates environment blockers from model repair failures.

## Candidate DeepSeek Command For Ready Shard

```bash
python3 -m repopilot.cli.run_benchmark data/swebench/lite_scale30.jsonl \
  --input-format swebench \
  --task-ids-file docs/reports/swebench_lite_scale30_non_astropy_task_ids.txt \
  --repo-cache-dir data/repos \
  --use-venv \
  --install-repo \
  --setup-command "python -m pip install 'pytest<8' 'click<8.2' 'numpy<2' 'scipy<1.10' 'pandas<2' simplejson pytz pytest-mock pytest-timeout pytest-rerunfailures pytest-remotedata" \
  --env-profiles-file configs/swebench_lite_scale30_env_profiles.json \
  --provider deepseek-tools \
  --model deepseek-v4-flash \
  --reasoning-effort max \
  --temperature 1.0 \
  --api-timeout-sec 180 \
  --max-steps 20 \
  --max-test-runs 6 \
  --model-retries 1 \
  --runs-dir runs_swebench_lite_scale30_non_astropy_tools \
  --trajectory-log data/trajectories/swebench_lite_scale30_non_astropy_tools.jsonl \
  --memory-store data/memory/swebench_lite_scale30_non_astropy_tools_memory.jsonl \
  --output data/benchmarks/swebench_lite_scale30_non_astropy_tools.json
```
