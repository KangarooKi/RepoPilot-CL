# Run Manifest: SWE-bench Lite Scale-30 Non-Astropy After Rescue

## Summary

| Field | Value |
|---|---|
| Created UTC | `2026-06-15T03:40:42+00:00` |
| Git Commit | `4a4e475a259a17fa0d8b4fd54a839209d2e80e9f` |
| Dataset | `data/swebench/lite_scale30.jsonl` |
| Task IDs | `docs/reports/swebench_lite_scale30_non_astropy_task_ids.txt` |
| Provider | `deepseek-tools` |
| Model | `deepseek-v4-flash` |
| Report JSON | `docs/reports/swebench_lite_scale30_non_astropy_tools_after_rescue.json` |
| Python | `3.10.11` |
| Platform | `macOS-26.4.1-arm64-arm-64bit` |

## Metrics

| Metric | Value |
|---|---:|
| total | 24 |
| resolved | 22 |
| resolved_rate | 0.916667 |
| avg_patch_lines | 23.417 |
| avg_model_steps | 12.458 |
| avg_tool_steps | 12.458 |
| avg_test_runs | 3.458 |
| model_error_tasks | 3 |
| timeout_tasks | 1 |

## Failure Types

| Failure Type | Tasks |
|---|---:|
| `model_timeout` | 1 |
| `resolved` | 22 |
| `unresolved_patch` | 1 |

## Command

```bash
python3 -m repopilot.cli.merge_benchmark_reports docs/reports/swebench_lite_scale30_non_astropy_tools_merged.json docs/reports/swebench_lite_scale30_non_astropy_rescue.json docs/reports/swebench_lite_scale30_non_astropy_rescue_remaining4.json --task-ids-file docs/reports/swebench_lite_scale30_non_astropy_task_ids.txt --require-task-count 24 --output-md docs/reports/swebench_lite_scale30_non_astropy_tools_after_rescue.md --output-json docs/reports/swebench_lite_scale30_non_astropy_tools_after_rescue.json --title 'SWE-bench Lite Scale-30 Non-Astropy DeepSeek Tools After Rescue'
```

## Artifacts

| Label | Path | Exists | Size Bytes | SHA256 |
|---|---|---:|---:|---|
| `dataset` | `data/swebench/lite_scale30.jsonl` | yes | 322760 | `e3d37aac794c5d07dd0f94776a10ecc2e30b32b0a98c6b1c733173fdb8e88d54` |
| `task_ids` | `docs/reports/swebench_lite_scale30_non_astropy_task_ids.txt` | yes | 592 | `30370469745ac932c24a6d196b704354c0658d9c38cd75abc4b037ce050ca3c9` |
| `report_json` | `docs/reports/swebench_lite_scale30_non_astropy_tools_after_rescue.json` | yes | 28970 | `4d7626eb2d4cb5c5b7bd2f5f6438536676f0e4bfb16c8af28d41defa92f0e51f` |
| `env_profiles` | `configs/swebench_lite_scale30_env_profiles.json` | yes | 698 | `f22ef961630df83c851d39d2e72017e12c60cc0f9701c226ee598f9cbe70d45f` |
| `initial_report` | `docs/reports/swebench_lite_scale30_non_astropy_tools_merged.json` | yes | 24527 | `28c302c976a95dec99cc4b69265f24e034126fee2a5d624416355c0e401ffb27` |
| `rescue_report` | `docs/reports/swebench_lite_scale30_non_astropy_rescue.json` | yes | 4072 | `019c2f6907fa085e94db42b0e0e15844233cbb1fd64164fb3da70cbab72b2489` |
| `rescue_remaining4` | `docs/reports/swebench_lite_scale30_non_astropy_rescue_remaining4.json` | yes | 6050 | `545b46d39ccb243c8d9bf996e6d99d808afc82a552b931002dce38422e3b702d` |
| `failure_hints` | `docs/reports/swebench_lite_scale30_non_astropy_failure_hints.json` | yes | 14107 | `31ac47b42c60a1c91372cb00f0bfbd131a4db4df675f255dc8f810203d2b62a4` |
| `comparison` | `docs/reports/swebench_lite_scale30_non_astropy_rescue_comparison.json` | yes | 9424 | `b5e2d80f1c8162b471b32f70f4677eb1671d4f3053361d6dc990085c9fe42327` |
| `suite_summary` | `docs/reports/swebench_lite_scale30_non_astropy_suite_summary.json` | yes | 3547 | `65093dacdf242d3eb9df9f4c33f3d7c65aee96a3337c6a47d3bbf1ea2056d3a6` |

## Notes

- Final score is produced by merging the initial DeepSeek tools run with failure-critic rescue shards.
- API keys are supplied via environment variables and are not stored in this manifest.
