# SWE-bench Lite Scale-30 Non-Astropy Artifact Validation

## Summary

| Metric | Value |
|---|---:|
| Passed | yes |
| Total Checks | 50 |
| Passed Checks | 50 |
| Failed Checks | 0 |

## Checks

| Target Type | Path | Check | Passed | Message |
|---|---|---|---:|---|
| `benchmark_report` | `docs/reports/swebench_lite_scale30_non_astropy_tools_after_rescue.json` | `total_matches_tasks` | yes | declared=24 computed=24 |
| `benchmark_report` | `docs/reports/swebench_lite_scale30_non_astropy_tools_after_rescue.json` | `resolved_matches_tasks` | yes | declared=22 computed=22 |
| `benchmark_report` | `docs/reports/swebench_lite_scale30_non_astropy_tools_after_rescue.json` | `resolved_rate_matches_tasks` | yes | declared=0.9166666666666666 computed=0.9166666666666666 |
| `benchmark_report` | `docs/reports/swebench_lite_scale30_non_astropy_tools_after_rescue.json` | `failure_types_match_tasks` | yes | declared={'model_timeout': 1, 'resolved': 22, 'unresolved_patch': 1} computed={'model_timeout': 1, 'resolved': 22, 'unresolved_patch': 1} |
| `comparison_report` | `docs/reports/swebench_lite_scale30_non_astropy_rescue_comparison.json` | `base_total_matches_tasks` | yes | declared=24 computed=24 |
| `comparison_report` | `docs/reports/swebench_lite_scale30_non_astropy_rescue_comparison.json` | `candidate_total_matches_tasks` | yes | declared=24 computed=24 |
| `comparison_report` | `docs/reports/swebench_lite_scale30_non_astropy_rescue_comparison.json` | `common_tasks_match_tasks` | yes | declared=24 computed=24 |
| `comparison_report` | `docs/reports/swebench_lite_scale30_non_astropy_rescue_comparison.json` | `resolved_counts_match_tasks` | yes | declared=(16, 22, 6) computed=(16, 22, 6) |
| `comparison_report` | `docs/reports/swebench_lite_scale30_non_astropy_rescue_comparison.json` | `status_counts_match_tasks` | yes | declared={'gained_tasks': 6, 'lost_tasks': 0, 'still_resolved': 16, 'still_unresolved': 2, 'base_only_tasks': 0, 'candidate_only_tasks': 0} computed={'gained_tasks': 6, 'lost_tasks': 0, 'still_resolved': 16, 'still_unresolved': 2, 'base_only_tasks': 0, 'candidate_only_tasks': 0} |
| `comparison_report` | `docs/reports/swebench_lite_scale30_non_astropy_rescue_comparison.json` | `failure_transitions_match_tasks` | yes | declared={'model_call_error -> resolved': 1, 'model_timeout -> model_timeout': 1, 'model_timeout -> resolved': 2, 'no_patch -> resolved': 1, 'repo_install_error -> resolved': 1, 'resolved -> resolved': 16, 'unresolved_patch -> resolved': 1, 'unresolved_patch -> unresolved_patch': 1} computed={'model_call_error -> resolved': 1, 'model_timeout -> model_timeout': 1, 'model_timeout -> resolved': 2, 'no_patch -> resolved': 1, 'repo_install_error -> resolved': 1, 'resolved -> resolved': 16, 'unresolved_patch -> resolved': 1, 'unresolved_patch -> unresolved_patch': 1} |
| `suite_report` | `docs/reports/swebench_lite_scale30_non_astropy_suite_summary.json` | `baseline_exists` | yes | baseline=initial entries=['initial', 'after_rescue'] |
| `suite_report` | `docs/reports/swebench_lite_scale30_non_astropy_suite_summary.json` | `initial:repo_total_matches_entry` | yes | declared=24 computed=24 |
| `suite_report` | `docs/reports/swebench_lite_scale30_non_astropy_suite_summary.json` | `initial:repo_resolved_matches_entry` | yes | declared=16 computed=16 |
| `suite_report` | `docs/reports/swebench_lite_scale30_non_astropy_suite_summary.json` | `initial:resolved_rate_matches_entry` | yes | declared=0.6666666666666666 computed=0.6666666666666666 |
| `suite_report` | `docs/reports/swebench_lite_scale30_non_astropy_suite_summary.json` | `initial:failure_types_sum_to_total` | yes | declared_total=24 failure_total=24 |
| `suite_report` | `docs/reports/swebench_lite_scale30_non_astropy_suite_summary.json` | `after_rescue:repo_total_matches_entry` | yes | declared=24 computed=24 |
| `suite_report` | `docs/reports/swebench_lite_scale30_non_astropy_suite_summary.json` | `after_rescue:repo_resolved_matches_entry` | yes | declared=22 computed=22 |
| `suite_report` | `docs/reports/swebench_lite_scale30_non_astropy_suite_summary.json` | `after_rescue:resolved_rate_matches_entry` | yes | declared=0.9166666666666666 computed=0.9166666666666666 |
| `suite_report` | `docs/reports/swebench_lite_scale30_non_astropy_suite_summary.json` | `after_rescue:failure_types_sum_to_total` | yes | declared_total=24 failure_total=24 |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `metrics_match_report_json` | yes | declared={'total': 24, 'resolved': 22, 'resolved_rate': 0.916667, 'failure_types': {'model_timeout': 1, 'resolved': 22, 'unresolved_patch': 1}} computed={'total': 24, 'resolved': 22, 'resolved_rate': 0.916667, 'failure_types': {'model_timeout': 1, 'resolved': 22, 'unresolved_patch': 1}} |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `dataset:artifact_exists` | yes | declared=True computed=True path=data/swebench/lite_scale30.jsonl |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `dataset:size_matches` | yes | declared=322760 computed=322760 |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `dataset:sha256_matches` | yes | declared=e3d37aac794c5d07dd0f94776a10ecc2e30b32b0a98c6b1c733173fdb8e88d54 computed=e3d37aac794c5d07dd0f94776a10ecc2e30b32b0a98c6b1c733173fdb8e88d54 |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `task_ids:artifact_exists` | yes | declared=True computed=True path=docs/reports/swebench_lite_scale30_non_astropy_task_ids.txt |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `task_ids:size_matches` | yes | declared=592 computed=592 |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `task_ids:sha256_matches` | yes | declared=30370469745ac932c24a6d196b704354c0658d9c38cd75abc4b037ce050ca3c9 computed=30370469745ac932c24a6d196b704354c0658d9c38cd75abc4b037ce050ca3c9 |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `report_json:artifact_exists` | yes | declared=True computed=True path=docs/reports/swebench_lite_scale30_non_astropy_tools_after_rescue.json |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `report_json:size_matches` | yes | declared=28970 computed=28970 |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `report_json:sha256_matches` | yes | declared=4d7626eb2d4cb5c5b7bd2f5f6438536676f0e4bfb16c8af28d41defa92f0e51f computed=4d7626eb2d4cb5c5b7bd2f5f6438536676f0e4bfb16c8af28d41defa92f0e51f |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `env_profiles:artifact_exists` | yes | declared=True computed=True path=configs/swebench_lite_scale30_env_profiles.json |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `env_profiles:size_matches` | yes | declared=698 computed=698 |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `env_profiles:sha256_matches` | yes | declared=f22ef961630df83c851d39d2e72017e12c60cc0f9701c226ee598f9cbe70d45f computed=f22ef961630df83c851d39d2e72017e12c60cc0f9701c226ee598f9cbe70d45f |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `initial_report:artifact_exists` | yes | declared=True computed=True path=docs/reports/swebench_lite_scale30_non_astropy_tools_merged.json |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `initial_report:size_matches` | yes | declared=24527 computed=24527 |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `initial_report:sha256_matches` | yes | declared=28c302c976a95dec99cc4b69265f24e034126fee2a5d624416355c0e401ffb27 computed=28c302c976a95dec99cc4b69265f24e034126fee2a5d624416355c0e401ffb27 |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `rescue_report:artifact_exists` | yes | declared=True computed=True path=docs/reports/swebench_lite_scale30_non_astropy_rescue.json |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `rescue_report:size_matches` | yes | declared=4072 computed=4072 |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `rescue_report:sha256_matches` | yes | declared=019c2f6907fa085e94db42b0e0e15844233cbb1fd64164fb3da70cbab72b2489 computed=019c2f6907fa085e94db42b0e0e15844233cbb1fd64164fb3da70cbab72b2489 |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `rescue_remaining4:artifact_exists` | yes | declared=True computed=True path=docs/reports/swebench_lite_scale30_non_astropy_rescue_remaining4.json |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `rescue_remaining4:size_matches` | yes | declared=6050 computed=6050 |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `rescue_remaining4:sha256_matches` | yes | declared=545b46d39ccb243c8d9bf996e6d99d808afc82a552b931002dce38422e3b702d computed=545b46d39ccb243c8d9bf996e6d99d808afc82a552b931002dce38422e3b702d |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `failure_hints:artifact_exists` | yes | declared=True computed=True path=docs/reports/swebench_lite_scale30_non_astropy_failure_hints.json |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `failure_hints:size_matches` | yes | declared=14107 computed=14107 |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `failure_hints:sha256_matches` | yes | declared=31ac47b42c60a1c91372cb00f0bfbd131a4db4df675f255dc8f810203d2b62a4 computed=31ac47b42c60a1c91372cb00f0bfbd131a4db4df675f255dc8f810203d2b62a4 |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `comparison:artifact_exists` | yes | declared=True computed=True path=docs/reports/swebench_lite_scale30_non_astropy_rescue_comparison.json |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `comparison:size_matches` | yes | declared=9424 computed=9424 |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `comparison:sha256_matches` | yes | declared=b5e2d80f1c8162b471b32f70f4677eb1671d4f3053361d6dc990085c9fe42327 computed=b5e2d80f1c8162b471b32f70f4677eb1671d4f3053361d6dc990085c9fe42327 |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `suite_summary:artifact_exists` | yes | declared=True computed=True path=docs/reports/swebench_lite_scale30_non_astropy_suite_summary.json |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `suite_summary:size_matches` | yes | declared=3547 computed=3547 |
| `run_manifest` | `docs/reports/swebench_lite_scale30_non_astropy_after_rescue_manifest.json` | `suite_summary:sha256_matches` | yes | declared=65093dacdf242d3eb9df9f4c33f3d7c65aee96a3337c6a47d3bbf1ea2056d3a6 computed=65093dacdf242d3eb9df9f4c33f3d7c65aee96a3337c6a47d3bbf1ea2056d3a6 |
