# SWE-bench Lite Scale-30 Non-Astropy DeepSeek Tools After Rescue

## Summary

| Metric | Value |
|---|---:|
| Tasks | 24 |
| Resolved | 22 |
| Resolved Rate | 0.917 |
| Avg Patch Lines | 23.4 |
| Avg Model Steps | 12.5 |
| Avg Tool Steps | 12.5 |
| Avg Test Runs | 3.5 |
| Model Error Tasks | 3 |
| Timeout Tasks | 1 |

## Failure Types

| Failure Type | Tasks |
|---|---:|
| `model_timeout` | 1 |
| `resolved` | 22 |
| `unresolved_patch` | 1 |

## Tasks

| Task | Resolved | Patch Lines | Model Steps | Tool Steps | Test Runs | Failure Type | Changed Files |
|---|---:|---:|---:|---:|---:|---|---|
| `sqlfluff__sqlfluff-1625` | yes | 13 | 8 | 8 | 3 | resolved | `src/sqlfluff/rules/L031.py` |
| `sqlfluff__sqlfluff-2419` | yes | 13 | 9 | 9 | 3 | resolved | `src/sqlfluff/rules/L060.py` |
| `sqlfluff__sqlfluff-1733` | yes | 30 | 16 | 16 | 4 | resolved | `src/sqlfluff/rules/L036.py` |
| `sqlfluff__sqlfluff-1517` | no | 0 | 3 | 3 | 1 | model_timeout | none |
| `sqlfluff__sqlfluff-1763` | yes | 51 | 21 | 21 | 4 | resolved | `src/sqlfluff/core/linter/linted_file.py` |
| `marshmallow-code__marshmallow-1359` | yes | 13 | 17 | 17 | 4 | resolved | `src/marshmallow/fields.py` |
| `marshmallow-code__marshmallow-1343` | yes | 38 | 24 | 24 | 6 | resolved | `src/marshmallow/marshalling.py`, `src/marshmallow/schema.py` |
| `pvlib__pvlib-python-1707` | yes | 17 | 11 | 11 | 6 | resolved | `pvlib/iam.py` |
| `pvlib__pvlib-python-1072` | yes | 13 | 8 | 8 | 4 | resolved | `pvlib/temperature.py` |
| `pvlib__pvlib-python-1606` | yes | 17 | 8 | 8 | 4 | resolved | `pvlib/tools.py` |
| `pvlib__pvlib-python-1854` | yes | 13 | 4 | 4 | 3 | resolved | `pvlib/pvsystem.py` |
| `pvlib__pvlib-python-1154` | yes | 14 | 8 | 8 | 3 | resolved | `pvlib/irradiance.py` |
| `pylint-dev__astroid-1978` | yes | 62 | 12 | 12 | 4 | resolved | `astroid/raw_building.py` |
| `pylint-dev__astroid-1333` | yes | 15 | 20 | 20 | 3 | resolved | `astroid/modutils.py` |
| `pylint-dev__astroid-1196` | yes | 23 | 15 | 15 | 3 | resolved | `astroid/nodes/node_classes.py` |
| `pylint-dev__astroid-1866` | yes | 13 | 6 | 6 | 3 | resolved | `astroid/brain/brain_builtin_inference.py` |
| `pylint-dev__astroid-1268` | yes | 14 | 17 | 17 | 4 | resolved | `astroid/nodes/as_string.py` |
| `pyvista__pyvista-4315` | no | 37 | 13 | 13 | 3 | unresolved_patch | `pyvista/core/grid.py` |
| `pydicom__pydicom-1694` | yes | 14 | 5 | 5 | 3 | resolved | `pydicom/dataset.py` |
| `pydicom__pydicom-1413` | yes | 13 | 9 | 9 | 3 | resolved | `pydicom/dataelem.py` |
| `pydicom__pydicom-901` | yes | 54 | 16 | 16 | 3 | resolved | `pydicom/config.py` |
| `pydicom__pydicom-1139` | yes | 32 | 19 | 19 | 4 | resolved | `pydicom/tests/test_valuerep.py`, `pydicom/valuerep.py` |
| `pydicom__pydicom-1256` | yes | 14 | 11 | 11 | 3 | resolved | `pydicom/jsonrep.py` |
| `django__django-10914` | yes | 39 | 19 | 19 | 2 | resolved | `django/conf/global_settings.py`, `docs/ref/settings.txt` |

## Case Studies

### `sqlfluff__sqlfluff-1625`

- Repository: `sqlfluff/sqlfluff`
- Issue: TSQL - L031 incorrectly triggers "Avoid using aliases in join condition" when no join present
- Outcome: yes; failure type: `resolved`
- Steps: model=8, tools=8, tests=3
- Changed files: `src/sqlfluff/rules/L031.py`

```diff
diff --git a/src/sqlfluff/rules/L031.py b/src/sqlfluff/rules/L031.py
index 838c6ce5d..6069afe70 100644
--- a/src/sqlfluff/rules/L031.py
+++ b/src/sqlfluff/rules/L031.py
@@ -211,7 +211,7 @@ class Rule_L031(BaseRule):
             violation_buff.append(
                 LintResult(
                     anchor=alias_info.alias_identifier_ref,
-                    description="Avoid using aliases in join condition",
+                    description="Avoid aliases in from clauses and join conditions.",
                     fixes=fixes,
                 )
             )
```

### `sqlfluff__sqlfluff-2419`

- Repository: `sqlfluff/sqlfluff`
- Issue: Rule L060 could give a specific error message
- Outcome: yes; failure type: `resolved`
- Steps: model=9, tools=9, tests=3
- Changed files: `src/sqlfluff/rules/L060.py`

```diff
diff --git a/src/sqlfluff/rules/L060.py b/src/sqlfluff/rules/L060.py
index 836941edc..296398895 100644
--- a/src/sqlfluff/rules/L060.py
+++ b/src/sqlfluff/rules/L060.py
@@ -59,4 +59,7 @@ class Rule_L060(BaseRule):
             ],
         )
 
-        return LintResult(context.segment, [fix])
+        return LintResult(
+            context.segment, [fix],
+            description=f"Use 'COALESCE' instead of '{context.segment.raw_upper}'.",
+        )
```

### `sqlfluff__sqlfluff-1733`

- Repository: `sqlfluff/sqlfluff`
- Issue: Extra space when first field moved to new line in a WITH statement
- Outcome: yes; failure type: `resolved`
- Steps: model=16, tools=16, tests=4
- Changed files: `src/sqlfluff/rules/L036.py`

```diff
diff --git a/src/sqlfluff/rules/L036.py b/src/sqlfluff/rules/L036.py
index ed5533b81..c848acaaf 100644
--- a/src/sqlfluff/rules/L036.py
+++ b/src/sqlfluff/rules/L036.py
@@ -118,7 +118,24 @@ class Rule_L036(BaseRule):
                     loop_while=lambda s: s.is_type("whitespace", "comma") or s.is_meta,
                 )
                 fixes += [LintFix("delete", ws) for ws in ws_to_delete]
-                fixes.append(LintFix("create", select_target, NewlineSegment()))
+                # When inserting a newline, also insert the appropriate
+                # indentation whitespace, using the first whitespace after
+                # the first newline as a template.
+                if i == 0 and select_targets_info.first_whitespace_idx != -1:
+                    indent_ws = segment.segments[
+                        select_targets_info.first_whitespace_idx
+                    ]
+                    fixes.append(
+                        LintFix(
+                            "create",
+                            select_target,
+                            [NewlineSegment(), WhitespaceSegment(raw=indent_ws.raw)],
+                        )
+                    )
+                else:
...
```

### `sqlfluff__sqlfluff-1517`

- Repository: `sqlfluff/sqlfluff`
- Issue: "Dropped elements in sequence matching" when doubled semicolon
- Outcome: no; failure type: `model_timeout`
- Steps: model=3, tools=3, tests=1
- Changed files: none

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

### `marshmallow-code__marshmallow-1359`

- Repository: `marshmallow-code/marshmallow`
- Issue: 3.0: DateTime fields cannot be used as inner field for List or Tuple fields
- Outcome: yes; failure type: `resolved`
- Steps: model=17, tools=17, tests=4
- Changed files: `src/marshmallow/fields.py`

```diff
diff --git a/src/marshmallow/fields.py b/src/marshmallow/fields.py
index 0b18e7dd..1609fa4f 100644
--- a/src/marshmallow/fields.py
+++ b/src/marshmallow/fields.py
@@ -1114,7 +1114,7 @@ class DateTime(Field):
         super()._bind_to_schema(field_name, schema)
         self.format = (
             self.format
-            or getattr(schema.opts, self.SCHEMA_OPTS_VAR_NAME)
+            or getattr(getattr(self.root, 'opts', None), self.SCHEMA_OPTS_VAR_NAME, None)
             or self.DEFAULT_FORMAT
         )
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

### `pvlib__pvlib-python-1707`

- Repository: `pvlib/pvlib-python`
- Issue: regression: iam.physical returns nan for aoi > 90° when n = 1
- Outcome: yes; failure type: `resolved`
- Steps: model=11, tools=11, tests=6
- Changed files: `pvlib/iam.py`

```diff
diff --git a/pvlib/iam.py b/pvlib/iam.py
index 3eaa6b4c..70960d34 100644
--- a/pvlib/iam.py
+++ b/pvlib/iam.py
@@ -215,6 +215,12 @@ def physical(aoi, n=1.526, K=4.0, L=0.002, *, n_ar=None):
     # incidence angle modifier
     iam = (tau_s + tau_p) / 2 / tau_0
 
+    # treat abs(aoi) >= 90 as zero iam
+    iam = np.where(np.abs(aoi) >= 90, 0.0, iam)
+
+    if isinstance(aoi, pd.Series):
+        iam = pd.Series(iam, index=aoi.index)
+
     return iam
```

### `pvlib__pvlib-python-1072`

- Repository: `pvlib/pvlib-python`
- Issue: temperature.fuentes errors when given tz-aware inputs on pandas>=1.0.0
- Outcome: yes; failure type: `resolved`
- Steps: model=8, tools=8, tests=4
- Changed files: `pvlib/temperature.py`

```diff
diff --git a/pvlib/temperature.py b/pvlib/temperature.py
index 1d98736b..eb46d518 100644
--- a/pvlib/temperature.py
+++ b/pvlib/temperature.py
@@ -599,7 +599,7 @@ def fuentes(poa_global, temp_air, wind_speed, noct_installed, module_height=5,
     # n.b. the way Fuentes calculates the first timedelta makes it seem like
     # the value doesn't matter -- rather than recreate it here, just assume
     # it's the same as the second timedelta:
-    timedelta_hours = np.diff(poa_global.index).astype(float) / 1e9 / 60 / 60
+    timedelta_hours = np.diff(poa_global.index.asi8) / 1e9 / 60 / 60
     timedelta_hours = np.append([timedelta_hours[0]], timedelta_hours)
 
     tamb_array = temp_air + 273.15
```

### `pvlib__pvlib-python-1606`

- Repository: `pvlib/pvlib-python`
- Issue: golden-section search fails when upper and lower bounds are equal
- Outcome: yes; failure type: `resolved`
- Steps: model=8, tools=8, tests=4
- Changed files: `pvlib/tools.py`

```diff
diff --git a/pvlib/tools.py b/pvlib/tools.py
index 991568f9..ed90be7c 100644
--- a/pvlib/tools.py
+++ b/pvlib/tools.py
@@ -348,6 +348,12 @@ def _golden_sect_DataFrame(params, lower, upper, func, atol=1e-8):
     df['VH'] = upper
     df['VL'] = lower
 
+    # if all upper and lower bounds are equal, no search needed
+    if np.all(df['VH'] == df['VL']):
+        df['V1'] = df['VL']
+        func_result = func(df, 'V1')
+        return func_result, df['V1']
+
     converged = False
     iterations = 0
```

### `pvlib__pvlib-python-1854`

- Repository: `pvlib/pvlib-python`
- Issue: PVSystem with single Array generates an error
- Outcome: yes; failure type: `resolved`
- Steps: model=4, tools=4, tests=3
- Changed files: `pvlib/pvsystem.py`

```diff
diff --git a/pvlib/pvsystem.py b/pvlib/pvsystem.py
index c277a778..1a6d32cd 100644
--- a/pvlib/pvsystem.py
+++ b/pvlib/pvsystem.py
@@ -220,6 +220,8 @@ class PVSystem:
                 strings_per_inverter,
                 array_losses_parameters,
             ),)
+        elif isinstance(arrays, Array):
+            self.arrays = (arrays,)
         elif len(arrays) == 0:
             raise ValueError("PVSystem must have at least one Array. "
                              "If you want to create a PVSystem instance "
```

### `pvlib__pvlib-python-1154`

- Repository: `pvlib/pvlib-python`
- Issue: pvlib.irradiance.reindl() model generates NaNs when GHI = 0
- Outcome: yes; failure type: `resolved`
- Steps: model=8, tools=8, tests=3
- Changed files: `pvlib/irradiance.py`

```diff
diff --git a/pvlib/irradiance.py b/pvlib/irradiance.py
index 65800300..cc9d0a4d 100644
--- a/pvlib/irradiance.py
+++ b/pvlib/irradiance.py
@@ -886,7 +886,8 @@ def reindl(surface_tilt, surface_azimuth, dhi, dni, ghi, dni_extra,
     # these are the () and [] sub-terms of the second term of eqn 8
     term1 = 1 - AI
     term2 = 0.5 * (1 + tools.cosd(surface_tilt))
-    term3 = 1 + np.sqrt(HB / ghi) * (tools.sind(0.5 * surface_tilt) ** 3)
+    ratio = np.divide(HB, ghi, out=np.zeros_like(HB), where=ghi>0)
+    term3 = 1 + np.sqrt(ratio) * (tools.sind(0.5 * surface_tilt) ** 3)
 
     sky_diffuse = dhi * (AI * Rb + term1 * term2 * term3)
     sky_diffuse = np.maximum(sky_diffuse, 0)
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

### `pylint-dev__astroid-1333`

- Repository: `pylint-dev/astroid`
- Issue: astroid 2.9.1 breaks pylint with missing __init__.py: F0010: error while code parsing: Unable to load file __init__.py
- Outcome: yes; failure type: `resolved`
- Steps: model=20, tools=20, tests=3
- Changed files: `astroid/modutils.py`

```diff
diff --git a/astroid/modutils.py b/astroid/modutils.py
index 6d698469..7018bb7b 100644
--- a/astroid/modutils.py
+++ b/astroid/modutils.py
@@ -308,7 +308,9 @@ def _get_relative_base_path(filename, path_to_check):
 def modpath_from_file_with_callback(filename, path=None, is_package_cb=None):
     filename = os.path.expanduser(_path_from_filename(filename))
     for pathname in itertools.chain(
-        path or [], map(_cache_normalize_path, sys.path), sys.path
+        map(_cache_normalize_path, path or []),
+        map(_cache_normalize_path, sys.path),
+        sys.path,
     ):
         if not pathname:
             continue
```

### `pylint-dev__astroid-1196`

- Repository: `pylint-dev/astroid`
- Issue: getitem does not infer the actual unpacked value
- Outcome: yes; failure type: `resolved`
- Steps: model=15, tools=15, tests=3
- Changed files: `astroid/nodes/node_classes.py`

```diff
diff --git a/astroid/nodes/node_classes.py b/astroid/nodes/node_classes.py
index 11136f8c..6864c8e5 100644
--- a/astroid/nodes/node_classes.py
+++ b/astroid/nodes/node_classes.py
@@ -2361,9 +2361,16 @@ class Dict(NodeNG, Instance):
             # TODO(cpopa): no support for overriding yet, {1:2, **{1: 3}}.
             if isinstance(key, DictUnpack):
                 try:
-                    return value.getitem(index, context)
-                except (AstroidTypeError, AstroidIndexError):
+                    for inferred_value in value.infer(context):
+                        if inferred_value is util.Uninferable:
+                            continue
+                        try:
+                            return inferred_value.getitem(index, context)
+                        except (AstroidTypeError, AstroidIndexError):
+                            continue
+                except InferenceError:
                     continue
+                continue
             for inferredkey in key.infer(context):
                 if inferredkey is util.Uninferable:
                     continue
```

### `pylint-dev__astroid-1866`

- Repository: `pylint-dev/astroid`
- Issue: "TypeError: unsupported format string passed to NoneType.__format__" while running type inference in version 2.12.x
- Outcome: yes; failure type: `resolved`
- Steps: model=6, tools=6, tests=3
- Changed files: `astroid/brain/brain_builtin_inference.py`

```diff
diff --git a/astroid/brain/brain_builtin_inference.py b/astroid/brain/brain_builtin_inference.py
index af1ddf4d..8402d87f 100644
--- a/astroid/brain/brain_builtin_inference.py
+++ b/astroid/brain/brain_builtin_inference.py
@@ -954,7 +954,7 @@ def _infer_str_format_call(
 
     try:
         formatted_string = format_template.format(*pos_values, **keyword_values)
-    except (IndexError, KeyError):
+    except (IndexError, KeyError, ValueError, TypeError):
         # If there is an IndexError there are too few arguments to interpolate
         return iter([util.Uninferable])
```

### `pylint-dev__astroid-1268`

- Repository: `pylint-dev/astroid`
- Issue: 'AsStringVisitor' object has no attribute 'visit_unknown'
- Outcome: yes; failure type: `resolved`
- Steps: model=17, tools=17, tests=4
- Changed files: `astroid/nodes/as_string.py`

```diff
diff --git a/astroid/nodes/as_string.py b/astroid/nodes/as_string.py
index 427ccc15..647f773f 100644
--- a/astroid/nodes/as_string.py
+++ b/astroid/nodes/as_string.py
@@ -98,6 +98,9 @@ class AsStringVisitor:
 
     # visit_<node> methods ###########################################
 
+    def visit_unknown(self, node):
+        return f"{node.qname()}.{node.name}()"
+
     def visit_await(self, node):
         return f"await {node.value.accept(self)}"
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

### `pydicom__pydicom-1694`

- Repository: `pydicom/pydicom`
- Issue: Dataset.to_json_dict can still generate exceptions when suppress_invalid_tags=True
- Outcome: yes; failure type: `resolved`
- Steps: model=5, tools=5, tests=3
- Changed files: `pydicom/dataset.py`

```diff
diff --git a/pydicom/dataset.py b/pydicom/dataset.py
index e323150110..a6f8879666 100644
--- a/pydicom/dataset.py
+++ b/pydicom/dataset.py
@@ -2492,8 +2492,8 @@ class Dataset:
         json_dataset = {}
         for key in self.keys():
             json_key = '{:08X}'.format(key)
-            data_element = self[key]
             try:
+                data_element = self[key]
                 json_dataset[json_key] = data_element.to_json_dict(
                     bulk_data_element_handler=bulk_data_element_handler,
                     bulk_data_threshold=bulk_data_threshold
```

### `pydicom__pydicom-1413`

- Repository: `pydicom/pydicom`
- Issue: Error : a bytes-like object is required, not 'MultiValue'
- Outcome: yes; failure type: `resolved`
- Steps: model=9, tools=9, tests=3
- Changed files: `pydicom/dataelem.py`

```diff
diff --git a/pydicom/dataelem.py b/pydicom/dataelem.py
index b2709f132f..46a73d33fd 100644
--- a/pydicom/dataelem.py
+++ b/pydicom/dataelem.py
@@ -439,7 +439,7 @@ class DataElement:
         if isinstance(val, (str, bytes)) and self.VR not in \
                 ['UT', 'ST', 'LT', 'FL', 'FD', 'AT', 'OB', 'OW', 'OF', 'SL',
                  'SQ', 'SS', 'UL', 'OB/OW', 'OW/OB', 'OB or OW',
-                 'OW or OB', 'UN'] and 'US' not in self.VR:
+                 'OW or OB', 'OD', 'OL', 'OV', 'UN'] and 'US' not in self.VR:
             try:
                 if _backslash_str in val:
                     val = cast(str, val).split(_backslash_str)
```

### `pydicom__pydicom-901`

- Repository: `pydicom/pydicom`
- Issue: pydicom should not define handler, formatter and log level.
- Outcome: yes; failure type: `resolved`
- Steps: model=16, tools=16, tests=3
- Changed files: `pydicom/config.py`

```diff
diff --git a/pydicom/config.py b/pydicom/config.py
index ae9c8bdf1e..f5f1830688 100644
--- a/pydicom/config.py
+++ b/pydicom/config.py
@@ -62,10 +62,7 @@ and datetime.time respectively. Default: False
 
 # Logging system and debug function to change logging level
 logger = logging.getLogger('pydicom')
-handler = logging.StreamHandler()
-formatter = logging.Formatter("%(message)s")
-handler.setFormatter(formatter)
-logger.addHandler(handler)
+logger.addHandler(logging.NullHandler())
 
 
 import pydicom.pixel_data_handlers.numpy_handler as np_handler  # noqa
@@ -110,7 +107,10 @@ syntax, then this fact is announced in a NotImplementedError exception.
 """
 
 
-def debug(debug_on=True):
+debugging = False
+
+
...
```

### `pydicom__pydicom-1139`

- Repository: `pydicom/pydicom`
- Issue: Make PersonName3 iterable
- Outcome: yes; failure type: `resolved`
- Steps: model=19, tools=19, tests=4
- Changed files: `pydicom/tests/test_valuerep.py`, `pydicom/valuerep.py`

```diff
diff --git a/pydicom/tests/test_valuerep.py b/pydicom/tests/test_valuerep.py
index 2a4644cc0d..c78a219602 100644
--- a/pydicom/tests/test_valuerep.py
+++ b/pydicom/tests/test_valuerep.py
@@ -461,7 +461,7 @@ class TestPersonName:
 
         # Test that next() doesn't work without instantiating an iterator
         pn4 = PersonName("SomeName")
-        with pytest.raises(AttributeError):
+        with pytest.raises(TypeError):
             next(pn4)
 
     def test_iterator(self):
diff --git a/pydicom/valuerep.py b/pydicom/valuerep.py
index e992f78722..fe4037cc80 100644
--- a/pydicom/valuerep.py
+++ b/pydicom/valuerep.py
@@ -756,6 +756,14 @@ class PersonName:
     def __hash__(self):
         return hash(self.components)
 
+    def __iter__(self):
+        """Iterate over the characters in the person name."""
+        return iter(str(self))
...
```

### `pydicom__pydicom-1256`

- Repository: `pydicom/pydicom`
- Issue: from_json does not correctly convert BulkDataURI's in SQ data elements
- Outcome: yes; failure type: `resolved`
- Steps: model=11, tools=11, tests=3
- Changed files: `pydicom/jsonrep.py`

```diff
diff --git a/pydicom/jsonrep.py b/pydicom/jsonrep.py
index c6ef519c31..52bf00ce09 100644
--- a/pydicom/jsonrep.py
+++ b/pydicom/jsonrep.py
@@ -226,7 +226,8 @@ class JsonDataElementConverter:
                     value_key = unique_value_keys[0]
                     elem = DataElement.from_json(
                         self.dataset_class, key, vr,
-                        val[value_key], value_key
+                        val[value_key], value_key,
+                        self.bulk_data_element_handler
                     )
                 ds.add(elem)
         return ds
```

### `django__django-10914`

- Repository: `django/django`
- Issue: Set default FILE_UPLOAD_PERMISSION to 0o644.
- Outcome: yes; failure type: `resolved`
- Steps: model=19, tools=19, tests=2
- Changed files: `django/conf/global_settings.py`, `docs/ref/settings.txt`

```diff
diff --git a/django/conf/global_settings.py b/django/conf/global_settings.py
index acee9887d2..bdeec80610 100644
--- a/django/conf/global_settings.py
+++ b/django/conf/global_settings.py
@@ -304,7 +304,7 @@ FILE_UPLOAD_TEMP_DIR = None
 
 # The numeric mode to set newly-uploaded files to. The value should be a mode
 # you'd pass directly to os.chmod; see https://docs.python.org/library/os.html#files-and-directories.
-FILE_UPLOAD_PERMISSIONS = None
+FILE_UPLOAD_PERMISSIONS = 0o644
 
 # The numeric mode to assign to newly-created directories, when uploading files.
 # The value should be a mode as you'd pass to os.chmod;
diff --git a/docs/ref/settings.txt b/docs/ref/settings.txt
index 46e99af993..2657be829c 100644
--- a/docs/ref/settings.txt
+++ b/docs/ref/settings.txt
@@ -1484,16 +1484,16 @@ This value mirrors the functionality and caveats of the
 ``FILE_UPLOAD_PERMISSIONS``
 ---------------------------
 
-Default: ``None``
+Default: ``0o644``
 
...
```
