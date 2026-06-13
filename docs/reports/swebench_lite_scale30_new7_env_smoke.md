# SWE-bench Lite Scale-30 New-7 Environment Smoke Report

## Summary

| Metric | Value |
|---|---:|
| Tasks | 7 |
| Resolved | 0 |
| Resolved Rate | 0.000 |
| Avg Patch Lines | 0.0 |
| Avg Model Steps | 0.0 |
| Avg Tool Steps | 0.0 |
| Avg Test Runs | 0.1 |
| Model Error Tasks | 0 |
| Timeout Tasks | 0 |

## Failure Types

| Failure Type | Tasks |
|---|---:|
| `repo_install_error` | 6 |
| `test_command_error` | 1 |

## Tasks

| Task | Resolved | Patch Lines | Model Steps | Tool Steps | Test Runs | Failure Type | Changed Files |
|---|---:|---:|---:|---:|---:|---|---|
| `astropy__astropy-12907` | no | 0 | 0 | 0 | 0 | repo_install_error | none |
| `astropy__astropy-14182` | no | 0 | 0 | 0 | 0 | repo_install_error | none |
| `astropy__astropy-14365` | no | 0 | 0 | 0 | 0 | repo_install_error | none |
| `astropy__astropy-14995` | no | 0 | 0 | 0 | 0 | repo_install_error | none |
| `astropy__astropy-6938` | no | 0 | 0 | 0 | 0 | repo_install_error | none |
| `astropy__astropy-7746` | no | 0 | 0 | 0 | 0 | repo_install_error | none |
| `django__django-10914` | no | 0 | 0 | 0 | 1 | test_command_error | none |

## Case Studies

### `astropy__astropy-12907`

- Repository: `astropy/astropy`
- Issue: Modeling's `separability_matrix` does not compute separability correctly for nested CompoundModels
- Outcome: no; failure type: `repo_install_error`
- Steps: model=0, tools=0, tests=0
- Changed files: none

### `astropy__astropy-14182`

- Repository: `astropy/astropy`
- Issue: Please support header rows in RestructuredText output
- Outcome: no; failure type: `repo_install_error`
- Steps: model=0, tools=0, tests=0
- Changed files: none

### `astropy__astropy-14365`

- Repository: `astropy/astropy`
- Issue: ascii.qdp Table format assumes QDP commands are upper case
- Outcome: no; failure type: `repo_install_error`
- Steps: model=0, tools=0, tests=0
- Changed files: none

### `astropy__astropy-14995`

- Repository: `astropy/astropy`
- Issue: In v5.3, NDDataRef mask propagation fails when one of the operand does not have a mask
- Outcome: no; failure type: `repo_install_error`
- Steps: model=0, tools=0, tests=0
- Changed files: none

### `astropy__astropy-6938`

- Repository: `astropy/astropy`
- Issue: Possible bug in io.fits related to D exponents
- Outcome: no; failure type: `repo_install_error`
- Steps: model=0, tools=0, tests=0
- Changed files: none

### `astropy__astropy-7746`

- Repository: `astropy/astropy`
- Issue: Issue when passing empty lists/arrays to WCS transformations
- Outcome: no; failure type: `repo_install_error`
- Steps: model=0, tools=0, tests=0
- Changed files: none

### `django__django-10914`

- Repository: `django/django`
- Issue: Set default FILE_UPLOAD_PERMISSION to 0o644.
- Outcome: no; failure type: `test_command_error`
- Steps: model=0, tools=0, tests=1
- Changed files: none
