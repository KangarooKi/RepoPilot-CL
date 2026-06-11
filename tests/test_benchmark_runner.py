from pathlib import Path
import unittest

from repopilot.agent.loop import AgentRunResult
from repopilot.benchmark.runner import discover_task_files, load_task_inputs, run_tasks
from repopilot.benchmark.task_loader import Task
from repopilot.trajectory.schema import Trajectory


class BenchmarkRunnerTest(unittest.TestCase):
    def test_discover_task_files_from_glob(self) -> None:
        files = discover_task_files(["tasks/toy/divide_by_zero/task.json"])

        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].name, "task.json")

    def test_run_tasks_summarizes_results(self) -> None:
        def run_one(task: Task) -> AgentRunResult:
            return AgentRunResult(
                task_id=task.task_id,
                resolved=True,
                patch="diff\n+line\n",
                workdir=Path("runs") / task.task_id,
                trajectory=Trajectory(task.task_id, task.repo, task.issue),
            )

        tasks = load_task_inputs([Path("tasks/toy/divide_by_zero/task.json")])
        summary = run_tasks(tasks, run_one)

        self.assertEqual(summary.total, 1)
        self.assertEqual(summary.resolved, 1)
        self.assertEqual(summary.resolved_rate, 1.0)
        self.assertEqual(summary.tasks[0].patch_lines, 2)


if __name__ == "__main__":
    unittest.main()
