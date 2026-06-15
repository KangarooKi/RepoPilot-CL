# SWE-bench Lite Scale-30 Non-Astropy Rescue Remaining-4

## Summary

| Metric | Value |
|---|---:|
| Tasks | 4 |
| Resolved | 3 |
| Resolved Rate | 0.750 |
| Avg Patch Lines | 47.0 |
| Avg Model Steps | 17.5 |
| Avg Tool Steps | 17.5 |
| Avg Test Runs | 4.2 |
| Model Error Tasks | 1 |
| Timeout Tasks | 0 |

## Failure Types

| Failure Type | Tasks |
|---|---:|
| `resolved` | 3 |
| `unresolved_patch` | 1 |

## Tasks

| Task | Resolved | Patch Lines | Model Steps | Tool Steps | Test Runs | Failure Type | Changed Files |
|---|---:|---:|---:|---:|---:|---|---|
| `sqlfluff__sqlfluff-1763` | yes | 51 | 21 | 21 | 4 | resolved | `src/sqlfluff/core/linter/linted_file.py` |
| `marshmallow-code__marshmallow-1343` | yes | 38 | 24 | 24 | 6 | resolved | `src/marshmallow/marshalling.py`, `src/marshmallow/schema.py` |
| `pylint-dev__astroid-1978` | yes | 62 | 12 | 12 | 4 | resolved | `astroid/raw_building.py` |
| `pyvista__pyvista-4315` | no | 37 | 13 | 13 | 3 | unresolved_patch | `pyvista/core/grid.py` |

## Case Studies

### `sqlfluff__sqlfluff-1763`

- Repository: `sqlfluff/sqlfluff`
- Issue: dbt postgres fix command errors with UnicodeEncodeError and also wipes the .sql file
- Outcome: yes; failure type: `resolved`
- Steps: model=21, tools=21, tests=4
- Changed files: `src/sqlfluff/core/linter/linted_file.py`

```diff
diff --git a/src/sqlfluff/core/linter/linted_file.py b/src/sqlfluff/core/linter/linted_file.py
index 3a8593edd..33c665097 100644
--- a/src/sqlfluff/core/linter/linted_file.py
+++ b/src/sqlfluff/core/linter/linted_file.py
@@ -7,6 +7,7 @@ post linting.
 
 import os
 import logging
+import tempfile
 from typing import (
     Any,
     Iterable,
@@ -493,7 +494,35 @@ class LintedFile(NamedTuple):
             if suffix:
                 root, ext = os.path.splitext(fname)
                 fname = root + suffix + ext
-            # Actually write the file.
-            with open(fname, "w", encoding=self.encoding) as f:
-                f.write(write_buff)
+            # Write the file safely.
+            LintedFile._safe_create_replace_file(
+                fname, write_buff, self.encoding
+            )
         return success
...
```

### `marshmallow-code__marshmallow-1343`

- Repository: `marshmallow-code/marshmallow`
- Issue: [version 2.20.0] TypeError: 'NoneType' object is not subscriptable
- Outcome: yes; failure type: `resolved`
- Steps: model=24, tools=24, tests=6
- Changed files: `src/marshmallow/marshalling.py`, `src/marshmallow/schema.py`

```diff
diff --git a/src/marshmallow/marshalling.py b/src/marshmallow/marshalling.py
index feb7d1aa..e60288cc 100644
--- a/src/marshmallow/marshalling.py
+++ b/src/marshmallow/marshalling.py
@@ -10,10 +10,8 @@ and from primitive types.
 
 from __future__ import unicode_literals
 
-import collections
-
+from marshmallow.compat import Mapping, text_type, iteritems
 from marshmallow.utils import is_collection, missing, set_value
-from marshmallow.compat import text_type, iteritems
 from marshmallow.exceptions import (
     ValidationError,
 )
@@ -250,7 +248,7 @@ class Unmarshaller(ErrorStore):
 
         ret = dict_class()
 
-        if not isinstance(data, collections.Mapping):
+        if not isinstance(data, Mapping):
             errors = self.get_errors(index=index)
             msg = 'Invalid input type.'
...
```

### `pylint-dev__astroid-1978`

- Repository: `pylint-dev/astroid`
- Issue: Deprecation warnings from numpy
- Outcome: yes; failure type: `resolved`
- Steps: model=12, tools=12, tests=4
- Changed files: `astroid/raw_building.py`

```diff
diff --git a/astroid/raw_building.py b/astroid/raw_building.py
index cc3aa015..fb9ef2fc 100644
--- a/astroid/raw_building.py
+++ b/astroid/raw_building.py
@@ -14,8 +14,37 @@ import os
 import sys
 import types
 import warnings
+import contextlib
+import io
+import logging
 from collections.abc import Iterable
 from typing import Any, Union
+logger = logging.getLogger(__name__)
+
+
+@contextlib.contextmanager
+def _ignore_warnings_and_capture_output():
+    """Suppress warnings and redirect stdout/stderr to logging."""
+    with warnings.catch_warnings():
+        warnings.simplefilter("ignore")
+        old_stdout = sys.stdout
+        old_stderr = sys.stderr
+        out_buf = io.StringIO()
...
```

### `pyvista__pyvista-4315`

- Repository: `pyvista/pyvista`
- Issue: Rectilinear grid does not allow Sequences as inputs
- Outcome: no; failure type: `unresolved_patch`
- Steps: model=13, tools=13, tests=3
- Changed files: `pyvista/core/grid.py`

```diff
diff --git a/pyvista/core/grid.py b/pyvista/core/grid.py
index 6ce23688e..8dc16e438 100644
--- a/pyvista/core/grid.py
+++ b/pyvista/core/grid.py
@@ -135,23 +135,25 @@ class RectilinearGrid(_vtk.vtkRectilinearGrid, Grid, RectilinearGridFilters):
                     self.shallow_copy(args[0])
             elif isinstance(args[0], (str, pathlib.Path)):
                 self._from_file(args[0], **kwargs)
-            elif isinstance(args[0], np.ndarray):
-                self._from_arrays(args[0], None, None, check_duplicates)
+            elif isinstance(args[0], (np.ndarray, Sequence)):
+                self._from_arrays(np.asarray(args[0]), None, None, check_duplicates)
             else:
                 raise TypeError(f'Type ({type(args[0])}) not understood by `RectilinearGrid`')
 
         elif len(args) == 3 or len(args) == 2:
-            arg0_is_arr = isinstance(args[0], np.ndarray)
-            arg1_is_arr = isinstance(args[1], np.ndarray)
+            arg0_is_arr = isinstance(args[0], (np.ndarray, Sequence))
+            arg1_is_arr = isinstance(args[1], (np.ndarray, Sequence))
             if len(args) == 3:
-                arg2_is_arr = isinstance(args[2], np.ndarray)
+                arg2_is_arr = isinstance(args[2], (np.ndarray, Sequence))
             else:
...
```
