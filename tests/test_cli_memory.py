import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from repopilot.cli.run_task import main as run_task_main
from repopilot.memory.store import JsonlMemoryStore


class CliMemoryTest(unittest.TestCase):
    def test_run_task_writes_and_retrieves_memory_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            memory_path = root / "memory.jsonl"
            trajectory_path = root / "trajectory.jsonl"
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = run_task_main(
                    [
                        "tasks/toy/divide_by_zero/task.json",
                        "--runs-dir",
                        str(root / "runs"),
                        "--trajectory-log",
                        str(trajectory_path),
                        "--memory-store",
                        str(memory_path),
                    ]
                )
                second_exit_code = run_task_main(
                    [
                        "tasks/toy/divide_by_zero/task.json",
                        "--runs-dir",
                        str(root / "runs"),
                        "--trajectory-log",
                        str(trajectory_path),
                        "--memory-store",
                        str(memory_path),
                    ]
                )
            records = JsonlMemoryStore(memory_path).load()
            trajectories = [
                json.loads(line)
                for line in trajectory_path.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(exit_code, 0)
        self.assertEqual(second_exit_code, 0)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].task_id, "toy_divide_by_zero")
        self.assertTrue(records[0].resolved)
        self.assertEqual(records[0].touched_files, ["calc.py"])
        second_retrieve = [
            step for step in trajectories[1]["steps"] if step["action"] == "retrieve_memory"
        ][0]
        self.assertEqual(second_retrieve["metadata"]["memory_ids"], [records[0].memory_id])


if __name__ == "__main__":
    unittest.main()
