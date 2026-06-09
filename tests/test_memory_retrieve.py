import unittest

from repopilot.memory.retrieve import KeywordMemoryRetriever
from repopilot.memory.schema import MemoryRecord


class MemoryRetrieveTest(unittest.TestCase):
    def test_keyword_retriever_returns_related_memory(self) -> None:
        records = [
            MemoryRecord(
                memory_id="m1",
                task_id="t1",
                repo="toy/calculator",
                issue_summary="divide by zero should return none",
                error_signature="ZeroDivisionError",
                touched_files=["calc.py"],
                patch_pattern="guard zero divisor",
                resolved=True,
            ),
            MemoryRecord(
                memory_id="m2",
                task_id="t2",
                repo="toy/strings",
                issue_summary="strip whitespace",
                error_signature="AssertionError",
                touched_files=["strings.py"],
                patch_pattern="call strip",
                resolved=True,
            ),
        ]
        retriever = KeywordMemoryRetriever(records)

        results = retriever.retrieve("ZeroDivisionError in divide", top_k=1)

        self.assertEqual(results[0].memory_id, "m1")


if __name__ == "__main__":
    unittest.main()

