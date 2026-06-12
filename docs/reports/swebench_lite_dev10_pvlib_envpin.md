# SWE-bench Lite Dev-10 pvlib Environment Pin Check

## Summary

| Metric | Value |
|---|---:|
| Tasks | 3 |
| Resolved | 0 |
| Resolved Rate | 0.000 |
| Avg Patch Lines | 0.0 |
| Avg Model Steps | 0.0 |
| Avg Tool Steps | 0.0 |
| Avg Test Runs | 1.0 |
| Model Error Tasks | 0 |
| Timeout Tasks | 0 |

## Tasks

| Task | Resolved | Patch Lines | Model Steps | Tool Steps | Test Runs | Failure Type | Changed Files |
|---|---:|---:|---:|---:|---:|---|---|
| `pvlib__pvlib-python-1707` | no | 0 | 0 | 0 | 1 | no_patch | none |
| `pvlib__pvlib-python-1072` | no | 0 | 0 | 0 | 1 | no_patch | none |
| `pvlib__pvlib-python-1606` | no | 0 | 0 | 0 | 1 | no_patch | none |

## Case Studies

### `pvlib__pvlib-python-1707`

- Repository: `pvlib/pvlib-python`
- Issue: regression: iam.physical returns nan for aoi > 90° when n = 1
- Outcome: no; failure type: `no_patch`
- Steps: model=0, tools=0, tests=1
- Changed files: none

### `pvlib__pvlib-python-1072`

- Repository: `pvlib/pvlib-python`
- Issue: temperature.fuentes errors when given tz-aware inputs on pandas>=1.0.0
- Outcome: no; failure type: `no_patch`
- Steps: model=0, tools=0, tests=1
- Changed files: none

### `pvlib__pvlib-python-1606`

- Repository: `pvlib/pvlib-python`
- Issue: golden-section search fails when upper and lower bounds are equal
- Outcome: no; failure type: `no_patch`
- Steps: model=0, tools=0, tests=1
- Changed files: none
