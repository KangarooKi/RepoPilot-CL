import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from repopilot.cli.build_critic_refinement_inputs import main as refine_inputs_main
from repopilot.cli.refine_critic_predictions import main as refine_predictions_main
from repopilot.critic.refine import (
    build_refinement_queries,
    build_refinement_row,
    collect_refinement_evidence,
    refine_prediction_row_with_evidence,
)


class CriticRefinementTest(unittest.TestCase):
    def test_collect_refinement_evidence_uses_queries_and_focus_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "parser.py").write_text(
                "def parse_sequence(tokens):\n    return list(tokens)\n",
                encoding="utf-8",
            )
            (root / "src" / "util.py").write_text(
                "def parse_sequence_util(tokens):\n    return list(tokens)\n",
                encoding="utf-8",
            )
            (root / "tests" / "test_parser.py").write_text(
                "from src.parser import parse_sequence\n",
                encoding="utf-8",
            )

            evidence = collect_refinement_evidence(
                prediction={
                    "failure_type": "needs_repair",
                    "focus_files": ["src/parser.py"],
                    "suggested_queries": ["parse_sequence"],
                    "avoid": [],
                    "next_steps": [],
                },
                repo_root=root,
                source_text="Issue mentions parse_sequence.",
                context_lines=1,
            )

        paths = [snippet.path for snippet in evidence.snippets]
        self.assertIn("src/parser.py", paths)
        self.assertIn("src/util.py", paths)
        self.assertIn("parse_sequence", evidence.render())
        self.assertEqual(evidence.missing_focus_files, [])

    def test_build_refinement_row_keeps_reference_target_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "src").mkdir()
            (root / "src" / "parser.py").write_text(
                "def parse_sequence(tokens):\n    return list(tokens)\n",
                encoding="utf-8",
            )
            row = build_refinement_row(
                {
                    "example_id": "ex-1",
                    "task_id": "task-1",
                    "repo": "toy/repo",
                    "schema_valid": True,
                    "prediction": {
                        "failure_type": "needs_repair",
                        "focus_files": ["src/other.py"],
                        "suggested_queries": ["parse_sequence"],
                        "avoid": ["Avoid broad rewrites."],
                        "next_steps": ["Inspect parser behavior."],
                    },
                    "reference": {
                        "failure_type": "needs_repair",
                        "focus_files": ["src/parser.py"],
                        "suggested_queries": [],
                        "avoid": [],
                        "next_steps": [],
                    },
                },
                source_row={
                    "example_id": "ex-1",
                    "task_id": "task-1",
                    "repo": "toy/repo",
                    "input_text": "Issue:\nparse_sequence returns the wrong type.",
                    "target": {
                        "failure_type": "needs_repair",
                        "focus_files": ["src/parser.py"],
                        "suggested_queries": [],
                        "avoid": [],
                        "next_steps": [],
                    },
                },
                repo_root=root,
                context_lines=1,
            )

        self.assertEqual(row["example_id"], "ex-1-refine")
        self.assertEqual(row["target"]["focus_files"], ["src/parser.py"])
        self.assertEqual(row["messages"][0]["role"], "system")
        self.assertIn("Previous critic prediction", row["input_text"])
        evidence = row["metadata"]["refinement_evidence"]
        self.assertTrue(evidence["snippets"])

    def test_build_refinement_queries_prefers_prediction_queries(self) -> None:
        queries = build_refinement_queries(
            {
                "failure_type": "needs_repair",
                "focus_files": ["src/parser.py"],
                "suggested_queries": ["parse_sequence"],
                "avoid": [],
                "next_steps": [],
            },
            source_text="Issue mentions parse_sequence and ParserState.",
            max_queries=4,
        )

        self.assertEqual(queries[0], "parse_sequence")
        self.assertIn("parser", [query.lower() for query in queries])

    def test_refinement_inputs_cli_writes_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repo = root / "repo"
            (repo / "src").mkdir(parents=True)
            (repo / "src" / "parser.py").write_text(
                "def parse_sequence(tokens):\n    return list(tokens)\n",
                encoding="utf-8",
            )
            predictions = root / "predictions.jsonl"
            source = root / "source.jsonl"
            output = root / "refine.jsonl"
            predictions.write_text(
                json.dumps(
                    {
                        "example_id": "ex-1",
                        "task_id": "task-1",
                        "repo": "toy/repo",
                        "valid_json": True,
                        "schema_valid": True,
                        "prediction": {
                            "failure_type": "needs_repair",
                            "focus_files": ["src/parser.py"],
                            "suggested_queries": ["parse_sequence"],
                            "avoid": [],
                            "next_steps": [],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            source.write_text(
                json.dumps(
                    {
                        "example_id": "ex-1",
                        "task_id": "task-1",
                        "repo": "toy/repo",
                        "input_text": "Issue:\nparse_sequence returns the wrong type.",
                        "target": {
                            "failure_type": "needs_repair",
                            "focus_files": ["src/parser.py"],
                            "suggested_queries": [],
                            "avoid": [],
                            "next_steps": [],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                code = refine_inputs_main(
                    [
                        str(predictions),
                        "--source-jsonl",
                        str(source),
                        "--output-jsonl",
                        str(output),
                        "--repo-root-template",
                        str(repo),
                        "--context-lines",
                        "1",
                    ]
                )
            summary = json.loads(stdout.getvalue())
            row = json.loads(output.read_text(encoding="utf-8").strip())

        self.assertEqual(code, 0)
        self.assertEqual(summary["examples"], 1)
        self.assertEqual(summary["with_snippets"], 1)
        self.assertEqual(row["source_kind"], "critic_refinement")
        self.assertIn("messages", row)

    def test_refine_prediction_row_expands_focus_files_from_evidence(self) -> None:
        refined = refine_prediction_row_with_evidence(
            {
                "task_id": "task-1",
                "valid_json": True,
                "schema_valid": True,
                "prediction": {
                    "failure_type": "needs_repair",
                    "focus_files": ["src/parser.py"],
                    "suggested_queries": ["parse_sequence"],
                    "avoid": [],
                    "next_steps": [],
                },
                "reference": {
                    "failure_type": "needs_repair",
                    "focus_files": ["src/util.py"],
                    "suggested_queries": [],
                    "avoid": [],
                    "next_steps": [],
                },
            },
            refinement_row={
                "task_id": "task-1",
                "metadata": {
                    "refinement_evidence": {
                        "snippets": [
                            {"path": "src/parser.py"},
                            {"path": "src/util.py"},
                        ]
                    }
                },
            },
            keep_original=1,
            max_focus_files=4,
        )

        self.assertEqual(
            refined["prediction"]["focus_files"],
            ["src/parser.py", "src/util.py"],
        )
        self.assertEqual(
            refined["refinement_strategy"],
            "retrieval_evidence_focus_expansion",
        )

    def test_refine_predictions_cli_writes_expanded_predictions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            predictions = root / "predictions.jsonl"
            refinement = root / "refinement.jsonl"
            output = root / "refined.jsonl"
            predictions.write_text(
                json.dumps(
                    {
                        "task_id": "task-1",
                        "valid_json": True,
                        "schema_valid": True,
                        "prediction": {
                            "failure_type": "needs_repair",
                            "focus_files": ["src/parser.py"],
                            "suggested_queries": ["parse_sequence"],
                            "avoid": [],
                            "next_steps": [],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            refinement.write_text(
                json.dumps(
                    {
                        "task_id": "task-1",
                        "metadata": {
                            "refinement_evidence": {
                                "snippets": [
                                    {"path": "src/parser.py"},
                                    {"path": "src/util.py"},
                                ]
                            }
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with contextlib.redirect_stdout(io.StringIO()):
                code = refine_predictions_main(
                    [
                        str(predictions),
                        "--refinement-jsonl",
                        str(refinement),
                        "--output-jsonl",
                        str(output),
                    ]
                )
            row = json.loads(output.read_text(encoding="utf-8").strip())

        self.assertEqual(code, 0)
        self.assertEqual(
            row["prediction"]["focus_files"],
            ["src/parser.py", "src/util.py"],
        )


if __name__ == "__main__":
    unittest.main()
