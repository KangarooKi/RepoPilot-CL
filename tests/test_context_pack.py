from pathlib import Path
import tempfile
import unittest

from repopilot.benchmark.task_loader import Task
from repopilot.context.pack import ContextPackBuilder, select_queries
from repopilot.sandbox.runner import SandboxRunner


class ContextPackTest(unittest.TestCase):
    def test_select_queries_prioritizes_issue_and_tests(self) -> None:
        task = Task(
            task_id="demo",
            repo="demo/repo",
            issue="Rule L060 should mention IFNULL.",
            test_command="python -m pytest test_rules.py::test_l060",
            fail_to_pass_tests=["test_rules.py::test_l060_ifnull"],
        )

        queries = select_queries(task, memories=[], max_queries=4)

        self.assertIn("L060", queries)
        self.assertIn("IFNULL", queries)

    def test_context_pack_reads_search_snippets_from_repo(self) -> None:
        task = Task(
            task_id="local_context",
            repo="local/context",
            issue="Return None when dividing by zero.",
            test_command="python -m unittest",
            initial_files={},
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workdir = root / "repo"
            workdir.mkdir()
            (workdir / "calc.py").write_text(
                "def divide(a, b):\n    return a / b\n",
                encoding="utf-8",
            )
            runner = SandboxRunner(root=root / "runs")
            builder = ContextPackBuilder(max_queries=6, max_snippets=2, context_lines=2)
            context = builder.build(
                task=task,
                workdir=workdir,
                runner=runner,
                memories=[],
            )

        rendered = context.render()

        self.assertTrue(any(snippet.path == "calc.py" for snippet in context.snippets))
        self.assertIn("def divide", rendered)


if __name__ == "__main__":
    unittest.main()
