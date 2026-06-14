# SWE-bench Lite Scale-30 Non-Astropy Env Retry

## Summary

| Metric | Value |
|---|---:|
| Tasks | 2 |
| Resolved | 0 |
| Resolved Rate | 0.000 |
| Avg Patch Lines | 0.0 |
| Avg Model Steps | 0.0 |
| Avg Tool Steps | 0.0 |
| Avg Test Runs | 0.5 |
| Model Error Tasks | 0 |
| Timeout Tasks | 0 |

## Failure Types

| Failure Type | Tasks |
|---|---:|
| `no_patch` | 1 |
| `repo_install_error` | 1 |

## Tasks

| Task | Resolved | Patch Lines | Model Steps | Tool Steps | Test Runs | Failure Type | Changed Files |
|---|---:|---:|---:|---:|---:|---|---|
| `pyvista__pyvista-4315` | no | 0 | 0 | 0 | 0 | repo_install_error | none |
| `pydicom__pydicom-1694` | no | 0 | 0 | 0 | 1 | no_patch | none |

## Case Studies

### `pyvista__pyvista-4315`

- Repository: `pyvista/pyvista`
- Issue: Rectilinear grid does not allow Sequences as inputs
- Outcome: no; failure type: `repo_install_error`
- Steps: model=0, tools=0, tests=0
- Changed files: none

### `pydicom__pydicom-1694`

- Repository: `pydicom/pydicom`
- Issue: Dataset.to_json_dict can still generate exceptions when suppress_invalid_tags=True
- Outcome: no; failure type: `no_patch`
- Steps: model=0, tools=0, tests=1
- Changed files: none
