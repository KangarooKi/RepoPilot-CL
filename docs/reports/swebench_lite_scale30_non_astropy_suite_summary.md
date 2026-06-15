# SWE-bench Lite Scale-30 Non-Astropy Suite Summary

Baseline: `initial`

## Variants

| Variant | Tasks | Resolved | Rate | Delta | Gained | Lost | Still Unresolved | Failure Types |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `initial` | 24 | 16 | 0.667 | 0 | 0 | 0 | 8 | `model_call_error`=1, `model_timeout`=3, `no_patch`=1, `repo_install_error`=1, `resolved`=16, `unresolved_patch`=2 |
| `after_rescue` | 24 | 22 | 0.917 | +6 | 6 | 0 | 2 | `model_timeout`=1, `resolved`=22, `unresolved_patch`=1 |

## Repository Breakdown

| Variant | Repository | Resolved | Total | Rate |
|---|---|---:|---:|---:|
| `initial` | `pvlib/pvlib-python` | 5 | 5 | 1.000 |
| `initial` | `pydicom/pydicom` | 5 | 5 | 1.000 |
| `initial` | `pylint-dev/astroid` | 4 | 5 | 0.800 |
| `initial` | `sqlfluff/sqlfluff` | 0 | 5 | 0.000 |
| `initial` | `marshmallow-code/marshmallow` | 1 | 2 | 0.500 |
| `initial` | `django/django` | 1 | 1 | 1.000 |
| `initial` | `pyvista/pyvista` | 0 | 1 | 0.000 |
| `after_rescue` | `pvlib/pvlib-python` | 5 | 5 | 1.000 |
| `after_rescue` | `pydicom/pydicom` | 5 | 5 | 1.000 |
| `after_rescue` | `pylint-dev/astroid` | 5 | 5 | 1.000 |
| `after_rescue` | `sqlfluff/sqlfluff` | 4 | 5 | 0.800 |
| `after_rescue` | `marshmallow-code/marshmallow` | 2 | 2 | 1.000 |
| `after_rescue` | `django/django` | 1 | 1 | 1.000 |
| `after_rescue` | `pyvista/pyvista` | 0 | 1 | 0.000 |

## Artifacts

- `initial`: `docs/reports/swebench_lite_scale30_non_astropy_tools_merged.json`
- `after_rescue`: `docs/reports/swebench_lite_scale30_non_astropy_tools_after_rescue.json`
