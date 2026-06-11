import unittest

from repopilot.agent.deepseek_provider import extract_unified_diff


class DeepSeekProviderTest(unittest.TestCase):
    def test_extract_unified_diff_from_markdown_fence(self) -> None:
        output = """Here is the patch:

```diff
diff --git a/calc.py b/calc.py
--- a/calc.py
+++ b/calc.py
@@ -1,2 +1,4 @@
 def divide(a, b):
+    if b == 0:
+        return None
     return a / b
```
"""

        diff = extract_unified_diff(output)

        self.assertTrue(diff.startswith("diff --git"))
        self.assertIn("if b == 0", diff)


if __name__ == "__main__":
    unittest.main()

