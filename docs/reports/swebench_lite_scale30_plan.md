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
| `test7` scale-out shard | 7 | partially unblocked | `docs/reports/swebench_lite_scale30_django_envfix.md`, `docs/reports/swebench_lite_scale30_astropy_envprofile.md` |
| remaining `dev23` new repos | 11 | needs repo-specific setup pins | `astroid` smoke exposed pip/build setup failure |

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

## Next Actions

1. Run the already calibrated `dev12` shard with DeepSeek once
   `DEEPSEEK_API_KEY` is available in the shell.
2. Re-run `test7` with `--env-profiles-file` and split the Astropy native build
   issue from real agent failures.
3. Add repo-specific setup profiles for `astroid`, `pydicom`, and `pyvista`.
4. Re-run environment smoke by repo shard until setup failures are separated
   from agent failures.
5. Merge shard reports into a true scale-30 score report.
6. Apply rescue and failure critic only to tasks that reach baseline verifier
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
