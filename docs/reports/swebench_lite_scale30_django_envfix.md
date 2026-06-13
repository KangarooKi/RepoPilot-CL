# SWE-bench Lite Scale-30 Django Env-Fix Smoke

## Summary

| Metric | Value |
|---|---:|
| Tasks | 1 |
| Resolved | 0 |
| Resolved Rate | 0.000 |
| Avg Patch Lines | 0.0 |
| Avg Model Steps | 0.0 |
| Avg Tool Steps | 0.0 |
| Avg Test Runs | 1.0 |
| Model Error Tasks | 0 |
| Timeout Tasks | 0 |

## Failure Types

| Failure Type | Tasks |
|---|---:|
| `no_patch` | 1 |

## Tasks

| Task | Resolved | Patch Lines | Model Steps | Tool Steps | Test Runs | Failure Type | Changed Files |
|---|---:|---:|---:|---:|---:|---|---|
| `django__django-10914` | no | 0 | 0 | 0 | 1 | no_patch | none |

## Case Studies

### `django__django-10914`

- Repository: `django/django`
- Issue: Set default FILE_UPLOAD_PERMISSION to 0o644.
- Outcome: no; failure type: `no_patch`
- Steps: model=0, tools=0, tests=1
- Changed files: none
