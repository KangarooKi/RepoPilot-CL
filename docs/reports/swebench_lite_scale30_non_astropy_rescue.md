# SWE-bench Lite Scale-30 Non-Astropy Rescue Partial

## Summary

| Metric | Value |
|---|---:|
| Tasks | 3 |
| Resolved | 3 |
| Resolved Rate | 1.000 |
| Avg Patch Lines | 18.7 |
| Avg Model Steps | 11.0 |
| Avg Tool Steps | 11.0 |
| Avg Test Runs | 3.3 |
| Model Error Tasks | 0 |
| Timeout Tasks | 0 |

## Failure Types

| Failure Type | Tasks |
|---|---:|
| `resolved` | 3 |

## Tasks

| Task | Resolved | Patch Lines | Model Steps | Tool Steps | Test Runs | Failure Type | Changed Files |
|---|---:|---:|---:|---:|---:|---|---|
| `sqlfluff__sqlfluff-1625` | yes | 13 | 8 | 8 | 3 | resolved | `src/sqlfluff/rules/L031.py` |
| `sqlfluff__sqlfluff-2419` | yes | 13 | 9 | 9 | 3 | resolved | `src/sqlfluff/rules/L060.py` |
| `sqlfluff__sqlfluff-1733` | yes | 30 | 16 | 16 | 4 | resolved | `src/sqlfluff/rules/L036.py` |

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
