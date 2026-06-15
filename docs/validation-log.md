# Validation Log

## 2026-06-15: Trajectory training dataset builder

- Added `python3 -m repopilot.cli.build_training_dataset` for turning agent
  trajectory JSONL logs into critic and reranker training examples.
- Critic examples use issue text, baseline/final verifier signals, and action
  traces to target failure type, focus files, suggested searches, and next-step
  hints.
- Reranker examples use issue/test signal plus the final candidate patch to
  target a binary resolved label and regression flag.

Validation:

```bash
python3 -m unittest tests.test_training_examples tests.test_failure_critic tests.test_reranker_dataset
python3 -m repopilot.cli.build_training_dataset data/trajectories/swebench_lite_scale30_non_astropy_tools_after_rescue.jsonl --output-jsonl docs/reports/swebench_lite_scale30_non_astropy_training_examples.jsonl --output-summary-json docs/reports/swebench_lite_scale30_non_astropy_training_dataset_summary.json --output-summary-md docs/reports/swebench_lite_scale30_non_astropy_training_dataset_summary.md --title "SWE-bench Lite Scale-30 Non-Astropy Training Dataset Summary"
```

Result: the scale-30 non-Astropy after-rescue trajectory log produced 47
training examples: 24 critic examples and 23 reranker examples. The one missing
reranker example is the unresolved timeout trajectory with no final patch.

## 2026-06-15: Benchmark report merge CLI

- Added `python3 -m repopilot.cli.merge_benchmark_reports` for merging
  benchmark shard reports and rescue reports into one canonical report.
- Merge behavior is task-id based: resolved rescue trajectories replace
  unresolved earlier trajectories; if two entries have the same resolved status,
  the later report wins.
- Supports `--task-ids-file` for stable benchmark ordering and
  `--require-task-count` for scale-out sanity checks.

Validation:

```bash
python3 -m unittest tests.test_benchmark_report
python3 -m unittest tests.test_benchmark_report tests.test_rescue_plan tests.test_failure_critic
python3 -m unittest discover -s tests
python3 -m repopilot.cli.merge_benchmark_reports docs/reports/swebench_lite_scale30_non_astropy_tools_merged.json docs/reports/swebench_lite_scale30_non_astropy_rescue.json docs/reports/swebench_lite_scale30_non_astropy_rescue_remaining4.json --task-ids-file docs/reports/swebench_lite_scale30_non_astropy_task_ids.txt --require-task-count 24 --output-md /private/tmp/repopilot_scale30_after_rescue_merged.md --output-json /private/tmp/repopilot_scale30_after_rescue_merged.json --title "SWE-bench Lite Scale-30 Non-Astropy DeepSeek Tools After Rescue"
```

Result: the merge CLI reproduced the existing after-rescue report exactly:
24 tasks, 22 resolved, 0.917 resolved rate.

## 2026-06-15: Benchmark report comparison CLI

- Added `python3 -m repopilot.cli.compare_benchmark_reports` for comparing two
  benchmark reports at task level.
- The comparison report tracks gained, lost, still-resolved, still-unresolved,
  base-only, and candidate-only tasks.
- It also records failure-type transitions, which makes rescue/critic/reranker
  improvements easier to audit than a single resolved-rate delta.

Validation:

```bash
python3 -m unittest tests.test_benchmark_compare tests.test_benchmark_report
python3 -m repopilot.cli.compare_benchmark_reports --base docs/reports/swebench_lite_scale30_non_astropy_tools_merged.json --candidate docs/reports/swebench_lite_scale30_non_astropy_tools_after_rescue.json --base-name initial --candidate-name after_rescue --task-ids-file docs/reports/swebench_lite_scale30_non_astropy_task_ids.txt --require-same-tasks --output-md docs/reports/swebench_lite_scale30_non_astropy_rescue_comparison.md --output-json docs/reports/swebench_lite_scale30_non_astropy_rescue_comparison.json --title "SWE-bench Lite Scale-30 Non-Astropy Rescue Comparison"
```

Result: the initial-to-after-rescue comparison shows +6 resolved tasks, 6 gained
tasks, 0 lost tasks, 16 still-resolved tasks, and 2 still-unresolved tasks.

## 2026-06-15: Benchmark suite summary CLI

- Added `python3 -m repopilot.cli.summarize_benchmark_suite` for producing
  ablation-style summary tables from multiple benchmark report JSON files.
- The suite report records total/resolved/rate, delta against a named baseline,
  gained/lost/still-unresolved counts, failure-type mix, and per-repository
  resolved rates for each variant.
- This is the evaluation table format intended for future baseline, memory,
  critic, reranker, and teacher-rescue comparisons.

Validation:

```bash
python3 -m unittest tests.test_benchmark_suite tests.test_benchmark_compare tests.test_benchmark_report
python3 -m repopilot.cli.summarize_benchmark_suite --report initial=docs/reports/swebench_lite_scale30_non_astropy_tools_merged.json --report after_rescue=docs/reports/swebench_lite_scale30_non_astropy_tools_after_rescue.json --baseline initial --require-same-tasks --output-md docs/reports/swebench_lite_scale30_non_astropy_suite_summary.md --output-json docs/reports/swebench_lite_scale30_non_astropy_suite_summary.json --title "SWE-bench Lite Scale-30 Non-Astropy Suite Summary"
```

Result: the suite report records `initial` at 16/24 and `after_rescue` at 22/24,
with +6 delta resolved, 6 gained tasks, 0 lost tasks, and 2 still-unresolved
tasks.

## 2026-06-15: Benchmark run manifest CLI

- Added `python3 -m repopilot.cli.write_run_manifest` for writing
  reproducibility cards for benchmark results.
- The manifest records run name, git commit, command, dataset, task ids,
  provider/model, report metrics, notes, runtime metadata, and SHA256 hashes for
  dataset/report/config artifacts.
- This gives future critic/reranker experiments a stable provenance layer:
  every ablation row can point to an exact report and its input artifacts.

Validation:

```bash
python3 -m unittest tests.test_run_manifest tests.test_benchmark_suite tests.test_benchmark_compare tests.test_benchmark_report
python3 -m repopilot.cli.write_run_manifest --name "SWE-bench Lite Scale-30 Non-Astropy After Rescue" --command "python3 -m repopilot.cli.merge_benchmark_reports docs/reports/swebench_lite_scale30_non_astropy_tools_merged.json docs/reports/swebench_lite_scale30_non_astropy_rescue.json docs/reports/swebench_lite_scale30_non_astropy_rescue_remaining4.json --task-ids-file docs/reports/swebench_lite_scale30_non_astropy_task_ids.txt --require-task-count 24 --output-md docs/reports/swebench_lite_scale30_non_astropy_tools_after_rescue.md --output-json docs/reports/swebench_lite_scale30_non_astropy_tools_after_rescue.json --title 'SWE-bench Lite Scale-30 Non-Astropy DeepSeek Tools After Rescue'" --dataset data/swebench/lite_scale30.jsonl --task-ids-file docs/reports/swebench_lite_scale30_non_astropy_task_ids.txt --provider deepseek-tools --model deepseek-v4-flash --report-json docs/reports/swebench_lite_scale30_non_astropy_tools_after_rescue.json --git-commit 4a4e475a259a17fa0d8b4fd54a839209d2e80e9f --artifact env_profiles=configs/swebench_lite_scale30_env_profiles.json --artifact initial_report=docs/reports/swebench_lite_scale30_non_astropy_tools_merged.json --artifact rescue_report=docs/reports/swebench_lite_scale30_non_astropy_rescue.json --artifact rescue_remaining4=docs/reports/swebench_lite_scale30_non_astropy_rescue_remaining4.json --artifact failure_hints=docs/reports/swebench_lite_scale30_non_astropy_failure_hints.json --artifact comparison=docs/reports/swebench_lite_scale30_non_astropy_rescue_comparison.json --artifact suite_summary=docs/reports/swebench_lite_scale30_non_astropy_suite_summary.json --note "Final score is produced by merging the initial DeepSeek tools run with failure-critic rescue shards." --note "API keys are supplied via environment variables and are not stored in this manifest." --output-md docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.md --output-json docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json
```

Result: the manifest records the after-rescue score as 22/24 with artifact
hashes for the dataset, task ids, environment profiles, initial report, rescue
reports, failure hints, comparison report, and suite summary.

## 2026-06-15: Benchmark artifact validation CLI

- Added `python3 -m repopilot.cli.validate_benchmark_artifacts` for consistency
  checks across benchmark reports, comparison reports, suite summaries, and run
  manifests.
- The validator recomputes report metrics, comparison transition counts, suite
  repository totals, manifest metrics, and artifact size/SHA256 hashes.
- It returns a nonzero exit code when any check fails, so it can serve as a
  local publication gate before adding new benchmark rows.

Validation:

```bash
python3 -m unittest tests.test_artifact_validation tests.test_run_manifest tests.test_benchmark_suite tests.test_benchmark_compare tests.test_benchmark_report
python3 -m repopilot.cli.validate_benchmark_artifacts --report docs/reports/swebench_lite_scale30_non_astropy_tools_after_rescue.json --comparison docs/reports/swebench_lite_scale30_non_astropy_rescue_comparison.json --suite docs/reports/swebench_lite_scale30_non_astropy_suite_summary.json --manifest docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json --output-md docs/reports/swebench_lite_scale30_non_astropy_artifact_validation.md --output-json docs/reports/swebench_lite_scale30_non_astropy_artifact_validation.json --title "SWE-bench Lite Scale-30 Non-Astropy Artifact Validation"
```

Result: the scale-30 non-Astropy artifact validation passed 50/50 checks with
0 failed checks.

## 2026-06-15: SWE-bench scale-30 non-Astropy failure-critic rescue

- Source score report:
  `docs/reports/swebench_lite_scale30_non_astropy_tools_merged.json`
- Rescue task ids:
  `docs/reports/swebench_lite_scale30_non_astropy_rescue_task_ids.txt`
- Failure hints:
  `docs/reports/swebench_lite_scale30_non_astropy_failure_hints.md`
- Rescue reports:
  `docs/reports/swebench_lite_scale30_non_astropy_rescue.md` and
  `docs/reports/swebench_lite_scale30_non_astropy_rescue_remaining4.md`
- Final merged report:
  `docs/reports/swebench_lite_scale30_non_astropy_tools_after_rescue.md`

The rescue stage used the failure critic to convert the 8 unresolved cases from
the first formal non-Astropy score into task-specific hints. The rerun kept the
same main coding model, `deepseek-v4-flash`, and used `deepseek-tools`,
`reasoning_effort=max`, `temperature=1.0`, `max_steps=24`,
`max_test_runs=8`, `model_retries=2`, and `api_timeout_sec=240`.

Result:

| Stage | Resolved / Tasks |
|---|---:|
| Initial formal non-Astropy score | 16 / 24 |
| First rescue shard | 3 / 3 |
| Remaining rescue shard | 3 / 4 |
| Final merged score after rescue | 22 / 24 |

Final merged failure types:

| Failure Type | Tasks |
|---|---:|
| `resolved` | 22 |
| `model_timeout` | 1 |
| `unresolved_patch` | 1 |

Remaining unresolved cases:

| Task | Failure Type | Note |
|---|---|---|
| `sqlfluff__sqlfluff-1517` | `model_timeout` | The rescue attempt stalled while waiting for the model response, so the merged result keeps the original timeout trajectory. |
| `pyvista__pyvista-4315` | `unresolved_patch` | The PyVista environment reaches verifier execution, but the generated patch still fails the target behavior. |

## 2026-06-15: SWE-bench scale-30 non-Astropy DeepSeek tools score

- Formal score shard: the 24 non-Astropy tasks listed in
  `docs/reports/swebench_lite_scale30_non_astropy_task_ids.txt`
- Model: `deepseek-v4-flash`
- Agent mode: `deepseek-tools`
- Reasoning: `reasoning_effort=max`, `temperature=1.0`
- Limits: `max_steps=20`, `max_test_runs=6`, `model_retries=1`
- Environment profiles:
  `configs/swebench_lite_scale30_env_profiles.json`

The run was split into smaller execution shards after PyVista setup proved slow.
The final merged report deduplicates by task id, preserves the canonical
non-Astropy task order, and prefers resolved trajectories when duplicate task
ids exist.

Generated score reports:

- Markdown:
  `docs/reports/swebench_lite_scale30_non_astropy_tools_merged.md`
- JSON:
  `docs/reports/swebench_lite_scale30_non_astropy_tools_merged.json`

Result:

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

Next validation step: build failure hints from the merged trajectory and run a
rescue shard over the 8 unresolved non-Astropy tasks.

## 2026-06-14: PyVista profile completes non-Astropy scale-30 readiness

- Added a `pyvista/pyvista` environment profile in
  `configs/swebench_lite_scale30_env_profiles.json`.
- The profile disables the runner's default editable install and performs the
  editable install inside `setup_command` with
  `pip install --timeout 180 --retries 10 --prefer-binary -e .`.
- Ran a one-task scripted smoke with no model/API calls:
  `pyvista__pyvista-4315`.
- Generated report:
  `docs/reports/swebench_lite_scale30_pyvista_envprofile.md`

Result:

| Task | Failure Type | Test Runs | Meaning |
|---|---|---:|---|
| `pyvista__pyvista-4315` | `no_patch` | 1 | Reaches baseline verifier; scripted no-patch failure is expected. |

Current non-Astropy scale-30 readiness: 24/24 tasks reach baseline verifier
execution. The remaining scale-30 environment blocker is the separate 6-task
Astropy native build shard.

## 2026-06-14: SWE-bench scale-30 non-Astropy environment smoke

- Added non-Astropy scale-30 task list:
  `docs/reports/swebench_lite_scale30_non_astropy_task_ids.txt`
- Ran a 24-task scripted environment smoke with no model/API calls.
- Generated reports:
  `docs/reports/swebench_lite_scale30_non_astropy_env_smoke.md` and
  `docs/reports/swebench_lite_scale30_non_astropy_env_smoke.json`
- Retried the two initial preparation failures and generated:
  `docs/reports/swebench_lite_scale30_non_astropy_env_retry.md` and
  `docs/reports/swebench_lite_scale30_non_astropy_env_retry.json`

Initial 24-task smoke:

| Failure Type | Tasks |
|---|---:|
| `no_patch` | 22 |
| `prepare_error` | 2 |

Retry of the two `prepare_error` tasks:

| Task | Result | Note |
|---|---|---|
| `pydicom__pydicom-1694` | `no_patch`, `test_runs=1` | Reaches baseline verifier. |
| `pyvista__pyvista-4315` | `repo_install_error`, `test_runs=0` | Clone succeeds, then pip dependency download from `files.pythonhosted.org` times out during editable install. |

Current non-Astropy readiness after this retry: 23/24 tasks reach baseline
verifier execution. The remaining non-Astropy blocker at this point was PyVista
dependency installation reliability, separate from model repair quality.

## 2026-06-14: SWE-bench scale-30 environment profiles

- Added repo/task-level environment profiles:
  `configs/swebench_lite_scale30_env_profiles.json`
- Added `--env-profiles-file` to `run_benchmark`.
- Added deterministic Django SWE-bench selector conversion:
  `test_method (module.Class)` -> `module.Class.test_method`, executed through
  `python3 tests/runtests.py`.

Validation:

```bash
python3 -m unittest tests.test_swebench_loader tests.test_environment_profiles
python3 -m unittest discover -s tests
python3 -m repopilot.cli.inspect_tasks data/swebench/lite_scale30.jsonl --input-format swebench
```

Result:

| Check | Outcome |
|---|---|
| Focused unit tests | `7` passed |
| Full unit suite | `73` passed |
| Django command inspection | `django__django-10914` now uses `python3 tests/runtests.py test_utils.tests.OverrideSettingsTests.test_override_file_upload_permissions` |

Smoke runs:

| Task | Result | Report |
|---|---|---|
| `django__django-10914` | reaches baseline verifier; scripted run classified as `no_patch` | `docs/reports/swebench_lite_scale30_django_envfix.md` |
| `astropy__astropy-14182` | profile moves past earlier Python packaging errors, then fails on local macOS native bundled cfitsio/zlib build | `docs/reports/swebench_lite_scale30_astropy_envprofile.md` |

The scale-30 plan was updated with the new profile file and current blocker:
`docs/reports/swebench_lite_scale30_plan.md`.

## 2026-06-13: SWE-bench Lite scale-30 shard construction

- Local task file: `data/swebench/lite_scale30.jsonl`
- Composition: first 23 rows from `dev` plus first 7 rows from `test`
- Scale plan: `docs/reports/swebench_lite_scale30_plan.md`
- New-7 environment smoke report:
  `docs/reports/swebench_lite_scale30_new7_env_smoke.md`

Task mix:

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

New-7 environment smoke:

```bash
python3 -m repopilot.cli.run_benchmark data/swebench/lite_scale30.jsonl \
  --input-format swebench \
  --task-id astropy__astropy-12907 \
  --task-id astropy__astropy-14182 \
  --task-id astropy__astropy-14365 \
  --task-id astropy__astropy-14995 \
  --task-id astropy__astropy-6938 \
  --task-id astropy__astropy-7746 \
  --task-id django__django-10914 \
  --provider scripted \
  --no-memory
```

Result:

| Failure Type | Tasks |
|---|---:|
| `repo_install_error` | 6 |
| `test_command_error` | 1 |

Engineering changes made during this stage:

- Added `test_command_error` classification to benchmark reports and failure
  critic hints so invalid SWE-bench test selectors are not confused with agent
  no-patch failures.

## 2026-06-13: SWE-bench Lite dev-23 scaling groundwork

- Dataset: `data/swebench/lite_dev_23.jsonl`
- Scale plan: `docs/reports/swebench_lite_dev23_scale_plan.md`
- Requested Hugging Face rows: 30
- Returned rows: 23

Task mix:

| Repository | Tasks |
|---|---:|
| `sqlfluff/sqlfluff` | 5 |
| `pvlib/pvlib-python` | 5 |
| `pylint-dev/astroid` | 5 |
| `pydicom/pydicom` | 5 |
| `marshmallow-code/marshmallow` | 2 |
| `pyvista/pyvista` | 1 |

Engineering changes made during this stage:

- Added benchmark-level prepare/setup failure capture so one environment
  failure no longer aborts the whole batch.
- Recorded prepare failures as unresolved trajectories with `prepare_error`
  steps and verifier-like metadata.
- Added setup-oriented failure types to benchmark reports and failure critic
  classification: `setup_error`, `repo_install_error`, `test_patch_error`, and
  `prepare_error`.
- Added a failure-type distribution table to benchmark Markdown/JSON reports.

Environment finding:

- The first expanded smoke reached `pylint-dev/astroid`, but pip dependency
  download from `files.pythonhosted.org` timed out. This is an environment
  setup issue, not a model repair failure. The next formal score run should use
  repo shards and pinned setup commands.

Dev-12 environment smoke:

```bash
python3 -m repopilot.cli.run_benchmark data/swebench/lite_dev_23.jsonl \
  --input-format swebench \
  --limit 12 \
  --repo-cache-dir data/repos \
  --use-venv \
  --install-repo \
  --setup-command "python -m pip install 'pytest<8' 'click<8.2' 'numpy<2' 'scipy<1.10' 'pandas<2' simplejson pytz pytest-mock pytest-timeout pytest-rerunfailures pytest-remotedata" \
  --provider scripted \
  --no-memory \
  --runs-dir runs_swebench_lite_dev12_env_smoke \
  --trajectory-log data/trajectories/swebench_lite_dev12_env_smoke.jsonl \
  --output data/benchmarks/swebench_lite_dev12_env_smoke.json
```

Result:

| Metric | Value |
|---|---:|
| Tasks | 12 |
| Prepare/setup errors | 0 |
| Baseline verifier steps | 12 |
| Model calls | 0 |

Generated smoke reports:

- Markdown: `docs/reports/swebench_lite_dev12_env_smoke.md`
- JSON: `docs/reports/swebench_lite_dev12_env_smoke.json`

Local regression suite:

```bash
python3 -m unittest discover -s tests
```

Result: `67` tests passed.

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
