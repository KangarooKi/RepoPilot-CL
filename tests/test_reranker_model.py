import contextlib
import io
from pathlib import Path
import tempfile
import unittest

from repopilot.cli.train_reranker import main as train_reranker_main
from repopilot.reranker.dataset import RerankerExample, write_reranker_examples
from repopilot.reranker.model import (
    LearnedPatchReranker,
    load_model,
    save_model,
    train_logistic_reranker,
)


class RerankerModelTest(unittest.TestCase):
    def test_logistic_reranker_learns_positive_patch_score(self) -> None:
        examples = _examples()
        model = train_logistic_reranker(examples, epochs=100, learning_rate=0.4)

        positive_probability = model.predict_probability(
            patch=examples[0].candidate_patch,
            issue=examples[0].issue,
            baseline_error=examples[0].failing_tests,
            memory_text=examples[0].retrieved_memory,
        )
        negative_probability = model.predict_probability(
            patch=examples[1].candidate_patch,
            issue=examples[1].issue,
            baseline_error=examples[1].failing_tests,
            memory_text=examples[1].retrieved_memory,
        )

        self.assertGreater(positive_probability, negative_probability)
        self.assertEqual(model.metrics["examples"], 2)

    def test_save_load_and_score_learned_reranker(self) -> None:
        model = train_logistic_reranker(_examples(), epochs=20)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "model.json"
            save_model(model, path)
            loaded = load_model(path)

        reranker = LearnedPatchReranker(loaded)
        score = reranker.score(
            "candidate",
            _positive_patch(),
            issue="divide by zero should return none",
            baseline_error="ZeroDivisionError",
        )

        self.assertGreaterEqual(score.pass_probability, 0.0)
        self.assertLessEqual(score.pass_probability, 1.0)

    def test_train_reranker_cli_writes_model(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset_path = root / "dataset.jsonl"
            model_path = root / "model.json"
            write_reranker_examples(_examples(), dataset_path)

            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = train_reranker_main(
                    [
                        str(dataset_path),
                        "--model-output",
                        str(model_path),
                        "--epochs",
                        "20",
                    ]
                )
            loaded = load_model(model_path)

        self.assertEqual(exit_code, 0)
        self.assertEqual(loaded.metrics["examples"], 2)


def _examples() -> list[RerankerExample]:
    return [
        RerankerExample(
            task_id="t1",
            candidate_id="good",
            issue="divide by zero should return none",
            failing_tests="ZeroDivisionError",
            repo_context="toy/calculator",
            retrieved_memory="guard zero divisor",
            candidate_patch=_positive_patch(),
            trajectory_summary="verify_baseline -> verify_candidate",
            resolved=True,
            regression=False,
        ),
        RerankerExample(
            task_id="t1",
            candidate_id="bad",
            issue="divide by zero should return none",
            failing_tests="ZeroDivisionError",
            repo_context="toy/calculator",
            retrieved_memory="guard zero divisor",
            candidate_patch=_negative_patch(),
            trajectory_summary="verify_baseline -> verify_candidate",
            resolved=False,
            regression=True,
        ),
    ]


def _positive_patch() -> str:
    return (
        "diff --git a/calc.py b/calc.py\n"
        "--- a/calc.py\n"
        "+++ b/calc.py\n"
        "@@ -1,2 +1,4 @@\n"
        " def divide(a, b):\n"
        "+    if b == 0:\n"
        "+        return None\n"
        "     return a / b\n"
    )


def _negative_patch() -> str:
    return (
        "diff --git a/calc.py b/calc.py\n"
        "--- a/calc.py\n"
        "+++ b/calc.py\n"
        "@@ -1,2 +1,3 @@\n"
        " def divide(a, b):\n"
        "+    assert b != 0\n"
        "     return a / b\n"
    )


if __name__ == "__main__":
    unittest.main()
