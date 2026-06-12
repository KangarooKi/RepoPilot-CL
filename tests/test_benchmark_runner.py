from pathlib import Path
import unittest

from repopilot.agent.loop import AgentRunResult
from repopilot.benchmark.runner import (
    discover_task_files,
    filter_tasks,
    load_task_inputs,
    run_tasks,
)
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

    def test_filter_tasks_by_repo_and_test_counts(self) -> None:
        tasks = load_task_inputs([Path("tasks/toy/divide_by_zero/task.json")])

        self.assertEqual(
            len(filter_tasks(tasks, repo_contains="calculator", max_pass_to_pass=1)),
            1,
        )
        self.assertEqual(
            len(filter_tasks(tasks, repo_contains="strings")),
            0,
        )

    def test_filter_tasks_by_task_id(self) -> None:
        tasks = load_task_inputs(
            [
                Path("tasks/toy/divide_by_zero/task.json"),
                Path("tasks/toy/off_by_one/task.json"),
            ]
        )

        filtered = filter_tasks(tasks, task_ids={"toy_off_by_one"})

        self.assertEqual([task.task_id for task in filtered], ["toy_off_by_one"])


if __name__ == "__main__":
    unittest.main()
