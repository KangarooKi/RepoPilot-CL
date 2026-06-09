from pathlib import Path
import unittest

from repopilot.benchmark.task_loader import load_task


class TaskLoaderTest(unittest.TestCase):
    def test_load_toy_task(self) -> None:
        task = load_task(Path("tasks/toy/divide_by_zero/task.json"))

        self.assertEqual(task.task_id, "toy_divide_by_zero")
        self.assertEqual(task.repo, "toy/calculator")
        self.assertIn("divide", task.issue.lower())
        self.assertIn("calc.py", task.initial_files)


if __name__ == "__main__":
    unittest.main()

