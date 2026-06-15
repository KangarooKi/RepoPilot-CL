# SWE-bench Lite Scale-30 Non-Astropy Rescue Comparison

## Summary

| Metric | Value |
|---|---:|
| Base report | `initial` |
| Candidate report | `after_rescue` |
| Base tasks | 24 |
| Candidate tasks | 24 |
| Common tasks | 24 |
| Base resolved | 16 |
| Candidate resolved | 22 |
| Delta resolved | +6 |
| Gained tasks | 6 |
| Lost tasks | 0 |
| Still resolved | 16 |
| Still unresolved | 2 |
| Base-only tasks | 0 |
| Candidate-only tasks | 0 |

## Failure Transitions

| Transition | Tasks |
|---|---:|
| `model_call_error -> resolved` | 1 |
| `model_timeout -> model_timeout` | 1 |
| `model_timeout -> resolved` | 2 |
| `no_patch -> resolved` | 1 |
| `repo_install_error -> resolved` | 1 |
| `resolved -> resolved` | 16 |
| `unresolved_patch -> resolved` | 1 |
| `unresolved_patch -> unresolved_patch` | 1 |

## Task Outcomes

| Task | Status | Base | Candidate | Repository | Issue |
|---|---|---|---|---|---|
| `sqlfluff__sqlfluff-1625` | `gained` | no / `model_call_error` | yes / `resolved` | `sqlfluff/sqlfluff` | TSQL - L031 incorrectly triggers "Avoid using aliases in join condition" when no join present |
| `sqlfluff__sqlfluff-2419` | `gained` | no / `model_timeout` | yes / `resolved` | `sqlfluff/sqlfluff` | Rule L060 could give a specific error message |
| `sqlfluff__sqlfluff-1733` | `gained` | no / `repo_install_error` | yes / `resolved` | `sqlfluff/sqlfluff` | Extra space when first field moved to new line in a WITH statement |
| `sqlfluff__sqlfluff-1517` | `still_unresolved` | no / `model_timeout` | no / `model_timeout` | `sqlfluff/sqlfluff` | "Dropped elements in sequence matching" when doubled semicolon |
| `sqlfluff__sqlfluff-1763` | `gained` | no / `no_patch` | yes / `resolved` | `sqlfluff/sqlfluff` | dbt postgres fix command errors with UnicodeEncodeError and also wipes the .sql file |
| `marshmallow-code__marshmallow-1359` | `still_resolved` | yes / `resolved` | yes / `resolved` | `marshmallow-code/marshmallow` | 3.0: DateTime fields cannot be used as inner field for List or Tuple fields |
| `marshmallow-code__marshmallow-1343` | `gained` | no / `model_timeout` | yes / `resolved` | `marshmallow-code/marshmallow` | [version 2.20.0] TypeError: 'NoneType' object is not subscriptable |
| `pvlib__pvlib-python-1707` | `still_resolved` | yes / `resolved` | yes / `resolved` | `pvlib/pvlib-python` | regression: iam.physical returns nan for aoi > 90° when n = 1 |
| `pvlib__pvlib-python-1072` | `still_resolved` | yes / `resolved` | yes / `resolved` | `pvlib/pvlib-python` | temperature.fuentes errors when given tz-aware inputs on pandas>=1.0.0 |
| `pvlib__pvlib-python-1606` | `still_resolved` | yes / `resolved` | yes / `resolved` | `pvlib/pvlib-python` | golden-section search fails when upper and lower bounds are equal |
| `pvlib__pvlib-python-1854` | `still_resolved` | yes / `resolved` | yes / `resolved` | `pvlib/pvlib-python` | PVSystem with single Array generates an error |
| `pvlib__pvlib-python-1154` | `still_resolved` | yes / `resolved` | yes / `resolved` | `pvlib/pvlib-python` | pvlib.irradiance.reindl() model generates NaNs when GHI = 0 |
| `pylint-dev__astroid-1978` | `gained` | no / `unresolved_patch` | yes / `resolved` | `pylint-dev/astroid` | Deprecation warnings from numpy |
| `pylint-dev__astroid-1333` | `still_resolved` | yes / `resolved` | yes / `resolved` | `pylint-dev/astroid` | astroid 2.9.1 breaks pylint with missing __init__.py: F0010: error while code parsing: Unable to load file __init__.py |
| `pylint-dev__astroid-1196` | `still_resolved` | yes / `resolved` | yes / `resolved` | `pylint-dev/astroid` | getitem does not infer the actual unpacked value |
| `pylint-dev__astroid-1866` | `still_resolved` | yes / `resolved` | yes / `resolved` | `pylint-dev/astroid` | "TypeError: unsupported format string passed to NoneType.__format__" while running type inference in version 2.12.x |
| `pylint-dev__astroid-1268` | `still_resolved` | yes / `resolved` | yes / `resolved` | `pylint-dev/astroid` | 'AsStringVisitor' object has no attribute 'visit_unknown' |
| `pyvista__pyvista-4315` | `still_unresolved` | no / `unresolved_patch` | no / `unresolved_patch` | `pyvista/pyvista` | Rectilinear grid does not allow Sequences as inputs |
| `pydicom__pydicom-1694` | `still_resolved` | yes / `resolved` | yes / `resolved` | `pydicom/pydicom` | Dataset.to_json_dict can still generate exceptions when suppress_invalid_tags=True |
| `pydicom__pydicom-1413` | `still_resolved` | yes / `resolved` | yes / `resolved` | `pydicom/pydicom` | Error : a bytes-like object is required, not 'MultiValue' |
| `pydicom__pydicom-901` | `still_resolved` | yes / `resolved` | yes / `resolved` | `pydicom/pydicom` | pydicom should not define handler, formatter and log level. |
| `pydicom__pydicom-1139` | `still_resolved` | yes / `resolved` | yes / `resolved` | `pydicom/pydicom` | Make PersonName3 iterable |
| `pydicom__pydicom-1256` | `still_resolved` | yes / `resolved` | yes / `resolved` | `pydicom/pydicom` | from_json does not correctly convert BulkDataURI's in SQ data elements |
| `django__django-10914` | `still_resolved` | yes / `resolved` | yes / `resolved` | `django/django` | Set default FILE_UPLOAD_PERMISSION to 0o644. |
