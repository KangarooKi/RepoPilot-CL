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
| non-Astropy scale-30 shard | 24 | 23 reach baseline verifier; 1 PyVista install timeout remains | `docs/reports/swebench_lite_scale30_non_astropy_env_smoke.md`, `docs/reports/swebench_lite_scale30_non_astropy_env_retry.md` |
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

Current non-Astropy readiness: 23/24 tasks reach the baseline verifier. The one
remaining non-Astropy blocker is PyVista dependency installation reliability, not
agent behavior.

## Next Actions

1. Add a PyVista task profile that disables the default editable install and
   performs `pip install --timeout 120 --retries 10 -e .` inside
   `setup_command`, then rerun `pyvista__pyvista-4315`.
2. Run DeepSeek on the 23 non-Astropy tasks that already reach baseline
   verifier execution.
3. Keep the 6 Astropy tasks as a separate Linux/container or native-build
   follow-up shard.
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
