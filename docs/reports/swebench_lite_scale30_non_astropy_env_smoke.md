# SWE-bench Lite Scale-30 Non-Astropy Env Smoke

## Summary

| Metric | Value |
|---|---:|
| Tasks | 24 |
| Resolved | 0 |
| Resolved Rate | 0.000 |
| Avg Patch Lines | 0.0 |
| Avg Model Steps | 0.0 |
| Avg Tool Steps | 0.0 |
| Avg Test Runs | 0.9 |
| Model Error Tasks | 0 |
| Timeout Tasks | 0 |

## Failure Types

| Failure Type | Tasks |
|---|---:|
| `no_patch` | 22 |
| `prepare_error` | 2 |

## Tasks

| Task | Resolved | Patch Lines | Model Steps | Tool Steps | Test Runs | Failure Type | Changed Files |
|---|---:|---:|---:|---:|---:|---|---|
| `sqlfluff__sqlfluff-1625` | no | 0 | 0 | 0 | 1 | no_patch | none |
| `sqlfluff__sqlfluff-2419` | no | 0 | 0 | 0 | 1 | no_patch | none |
| `sqlfluff__sqlfluff-1733` | no | 0 | 0 | 0 | 1 | no_patch | none |
| `sqlfluff__sqlfluff-1517` | no | 0 | 0 | 0 | 1 | no_patch | none |
| `sqlfluff__sqlfluff-1763` | no | 0 | 0 | 0 | 1 | no_patch | none |
| `marshmallow-code__marshmallow-1359` | no | 0 | 0 | 0 | 1 | no_patch | none |
| `marshmallow-code__marshmallow-1343` | no | 0 | 0 | 0 | 1 | no_patch | none |
| `pvlib__pvlib-python-1707` | no | 0 | 0 | 0 | 1 | no_patch | none |
| `pvlib__pvlib-python-1072` | no | 0 | 0 | 0 | 1 | no_patch | none |
| `pvlib__pvlib-python-1606` | no | 0 | 0 | 0 | 1 | no_patch | none |
| `pvlib__pvlib-python-1854` | no | 0 | 0 | 0 | 1 | no_patch | none |
| `pvlib__pvlib-python-1154` | no | 0 | 0 | 0 | 1 | no_patch | none |
| `pylint-dev__astroid-1978` | no | 0 | 0 | 0 | 1 | no_patch | none |
| `pylint-dev__astroid-1333` | no | 0 | 0 | 0 | 1 | no_patch | none |
| `pylint-dev__astroid-1196` | no | 0 | 0 | 0 | 1 | no_patch | none |
| `pylint-dev__astroid-1866` | no | 0 | 0 | 0 | 1 | no_patch | none |
| `pylint-dev__astroid-1268` | no | 0 | 0 | 0 | 1 | no_patch | none |
| `pyvista__pyvista-4315` | no | 0 | 0 | 0 | 0 | prepare_error | none |
| `pydicom__pydicom-1694` | no | 0 | 0 | 0 | 0 | prepare_error | none |
| `pydicom__pydicom-1413` | no | 0 | 0 | 0 | 1 | no_patch | none |
| `pydicom__pydicom-901` | no | 0 | 0 | 0 | 1 | no_patch | none |
| `pydicom__pydicom-1139` | no | 0 | 0 | 0 | 1 | no_patch | none |
| `pydicom__pydicom-1256` | no | 0 | 0 | 0 | 1 | no_patch | none |
| `django__django-10914` | no | 0 | 0 | 0 | 1 | no_patch | none |

## Case Studies

### `sqlfluff__sqlfluff-1625`

- Repository: `sqlfluff/sqlfluff`
- Issue: TSQL - L031 incorrectly triggers "Avoid using aliases in join condition" when no join present
- Outcome: no; failure type: `no_patch`
- Steps: model=0, tools=0, tests=1
- Changed files: none

### `sqlfluff__sqlfluff-2419`

- Repository: `sqlfluff/sqlfluff`
- Issue: Rule L060 could give a specific error message
- Outcome: no; failure type: `no_patch`
- Steps: model=0, tools=0, tests=1
- Changed files: none

### `sqlfluff__sqlfluff-1733`

- Repository: `sqlfluff/sqlfluff`
- Issue: Extra space when first field moved to new line in a WITH statement
- Outcome: no; failure type: `no_patch`
- Steps: model=0, tools=0, tests=1
- Changed files: none

### `sqlfluff__sqlfluff-1517`

- Repository: `sqlfluff/sqlfluff`
- Issue: "Dropped elements in sequence matching" when doubled semicolon
- Outcome: no; failure type: `no_patch`
- Steps: model=0, tools=0, tests=1
- Changed files: none

### `sqlfluff__sqlfluff-1763`

- Repository: `sqlfluff/sqlfluff`
- Issue: dbt postgres fix command errors with UnicodeEncodeError and also wipes the .sql file
- Outcome: no; failure type: `no_patch`
- Steps: model=0, tools=0, tests=1
- Changed files: none

### `marshmallow-code__marshmallow-1359`

- Repository: `marshmallow-code/marshmallow`
- Issue: 3.0: DateTime fields cannot be used as inner field for List or Tuple fields
- Outcome: no; failure type: `no_patch`
- Steps: model=0, tools=0, tests=1
- Changed files: none

### `marshmallow-code__marshmallow-1343`

- Repository: `marshmallow-code/marshmallow`
- Issue: [version 2.20.0] TypeError: 'NoneType' object is not subscriptable
- Outcome: no; failure type: `no_patch`
- Steps: model=0, tools=0, tests=1
- Changed files: none

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

### `pvlib__pvlib-python-1854`

- Repository: `pvlib/pvlib-python`
- Issue: PVSystem with single Array generates an error
- Outcome: no; failure type: `no_patch`
- Steps: model=0, tools=0, tests=1
- Changed files: none

### `pvlib__pvlib-python-1154`

- Repository: `pvlib/pvlib-python`
- Issue: pvlib.irradiance.reindl() model generates NaNs when GHI = 0
- Outcome: no; failure type: `no_patch`
- Steps: model=0, tools=0, tests=1
- Changed files: none

### `pylint-dev__astroid-1978`

- Repository: `pylint-dev/astroid`
- Issue: Deprecation warnings from numpy
- Outcome: no; failure type: `no_patch`
- Steps: model=0, tools=0, tests=1
- Changed files: none

### `pylint-dev__astroid-1333`

- Repository: `pylint-dev/astroid`
- Issue: astroid 2.9.1 breaks pylint with missing __init__.py: F0010: error while code parsing: Unable to load file __init__.py
- Outcome: no; failure type: `no_patch`
- Steps: model=0, tools=0, tests=1
- Changed files: none

### `pylint-dev__astroid-1196`

- Repository: `pylint-dev/astroid`
- Issue: getitem does not infer the actual unpacked value
- Outcome: no; failure type: `no_patch`
- Steps: model=0, tools=0, tests=1
- Changed files: none

### `pylint-dev__astroid-1866`

- Repository: `pylint-dev/astroid`
- Issue: "TypeError: unsupported format string passed to NoneType.__format__" while running type inference in version 2.12.x
- Outcome: no; failure type: `no_patch`
- Steps: model=0, tools=0, tests=1
- Changed files: none

### `pylint-dev__astroid-1268`

- Repository: `pylint-dev/astroid`
- Issue: 'AsStringVisitor' object has no attribute 'visit_unknown'
- Outcome: no; failure type: `no_patch`
- Steps: model=0, tools=0, tests=1
- Changed files: none

### `pyvista__pyvista-4315`

- Repository: `pyvista/pyvista`
- Issue: Rectilinear grid does not allow Sequences as inputs
- Outcome: no; failure type: `prepare_error`
- Steps: model=0, tools=0, tests=0
- Changed files: none

### `pydicom__pydicom-1694`

- Repository: `pydicom/pydicom`
- Issue: Dataset.to_json_dict can still generate exceptions when suppress_invalid_tags=True
- Outcome: no; failure type: `prepare_error`
- Steps: model=0, tools=0, tests=0
- Changed files: none

### `pydicom__pydicom-1413`

- Repository: `pydicom/pydicom`
- Issue: Error : a bytes-like object is required, not 'MultiValue'
- Outcome: no; failure type: `no_patch`
- Steps: model=0, tools=0, tests=1
- Changed files: none

### `pydicom__pydicom-901`

- Repository: `pydicom/pydicom`
- Issue: pydicom should not define handler, formatter and log level.
- Outcome: no; failure type: `no_patch`
- Steps: model=0, tools=0, tests=1
- Changed files: none

### `pydicom__pydicom-1139`

- Repository: `pydicom/pydicom`
- Issue: Make PersonName3 iterable
- Outcome: no; failure type: `no_patch`
- Steps: model=0, tools=0, tests=1
- Changed files: none

### `pydicom__pydicom-1256`

- Repository: `pydicom/pydicom`
- Issue: from_json does not correctly convert BulkDataURI's in SQ data elements
- Outcome: no; failure type: `no_patch`
- Steps: model=0, tools=0, tests=1
- Changed files: none

### `django__django-10914`

- Repository: `django/django`
- Issue: Set default FILE_UPLOAD_PERMISSION to 0o644.
- Outcome: no; failure type: `no_patch`
- Steps: model=0, tools=0, tests=1
- Changed files: none
