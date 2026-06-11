import unittest

from repopilot.memory.distill import (
    extract_error_signature,
    extract_touched_files,
    memory_from_trajectory,
)
from repopilot.memory.retrieve import KeywordMemoryRetriever
from repopilot.memory.schema import MemoryRecord
from repopilot.memory.store import JsonlMemoryStore
from repopilot.trajectory.schema import Trajectory


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

    def test_memory_distiller_extracts_patch_and_error_signal(self) -> None:
        trajectory = Trajectory(
            task_id="toy_divide",
            repo="toy/calculator",
            issue="Divide by zero should return None.",
            final_patch=(
                "diff --git a/calc.py b/calc.py\n"
                "--- a/calc.py\n"
                "+++ b/calc.py\n"
                "@@ -1,2 +1,4 @@\n"
                " def divide(a, b):\n"
                "+    if b == 0:\n"
                "+        return None\n"
                "     return a / b\n"
            ),
            resolved=True,
        )
        trajectory.add_step(
            "verify_baseline",
            "ZeroDivisionError: division by zero",
            {"error_summary": "ZeroDivisionError: division by zero"},
        )

        record = memory_from_trajectory(trajectory)

        self.assertEqual(record.task_id, "toy_divide")
        self.assertEqual(record.touched_files, ["calc.py"])
        self.assertEqual(record.error_signature, "ZeroDivisionError")
        self.assertIn("resolved=True", record.patch_pattern)
        self.assertTrue(record.memory_id.startswith("mem-"))

    def test_extract_touched_files_handles_multiple_diffs(self) -> None:
        diff = (
            "diff --git a/a.py b/a.py\n"
            "--- a/a.py\n"
            "+++ b/a.py\n"
            "diff --git a/pkg/b.py b/pkg/b.py\n"
            "--- a/pkg/b.py\n"
            "+++ b/pkg/b.py\n"
        )

        self.assertEqual(extract_touched_files(diff), ["a.py", "pkg/b.py"])

    def test_extract_error_signature_falls_back_to_verifier(self) -> None:
        trajectory = Trajectory(
            task_id="t",
            repo="r",
            issue="issue",
            verifier={"error_summary": "AssertionError: expected 1"},
        )

        self.assertEqual(extract_error_signature(trajectory), "AssertionError")

    def test_memory_store_upsert_replaces_existing_record(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            path = f"{temp_dir}/memory.jsonl"
            store = JsonlMemoryStore(path)
            first = MemoryRecord(
                memory_id="mem-1",
                task_id="t1",
                repo="repo",
                issue_summary="old",
                error_signature="AssertionError",
                touched_files=["a.py"],
                patch_pattern="old pattern",
                resolved=False,
            )
            second = MemoryRecord(
                memory_id="mem-1",
                task_id="t1",
                repo="repo",
                issue_summary="new",
                error_signature="AssertionError",
                touched_files=["b.py"],
                patch_pattern="new pattern",
                resolved=True,
            )

            store.upsert(first)
            store.upsert(second)
            records = store.load()

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].issue_summary, "new")
        self.assertTrue(records[0].resolved)


if __name__ == "__main__":
    unittest.main()
