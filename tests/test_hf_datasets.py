import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from repopilot.benchmark.hf_datasets import (
    HFDatasetRowsRequest,
    fetch_rows,
    write_jsonl,
)


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return json.dumps(
            {
                "rows": [
                    {
                        "row_idx": 0,
                        "row": {
                            "repo": "demo/repo",
                            "instance_id": "demo__repo-1",
                            "base_commit": "abc123",
                            "problem_statement": "Fix bug.",
                            "FAIL_TO_PASS": "[]",
                            "PASS_TO_PASS": "[]",
                        },
                    }
                ]
            }
        ).encode("utf-8")


class HFDatasetsTest(unittest.TestCase):
    def test_request_url_encodes_dataset_id(self) -> None:
        request = HFDatasetRowsRequest(
            dataset="princeton-nlp/SWE-bench_Lite",
            split="dev",
            length=2,
        )

        url = request.url()

        self.assertIn("dataset=princeton-nlp%2FSWE-bench_Lite", url)
        self.assertIn("split=dev", url)
        self.assertIn("length=2", url)

    def test_fetch_rows_reads_row_payloads(self) -> None:
        def fake_urlopen(request, context, timeout):
            return _FakeResponse()

        with patch("urllib.request.urlopen", fake_urlopen):
            rows = fetch_rows(HFDatasetRowsRequest("demo/dataset"))

        self.assertEqual(rows[0]["instance_id"], "demo__repo-1")

    def test_write_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = write_jsonl([{"a": 1}, {"b": 2}], Path(temp_dir) / "rows.jsonl")
            lines = output.read_text(encoding="utf-8").splitlines()

        self.assertEqual(lines, ['{"a": 1}', '{"b": 2}'])


if __name__ == "__main__":
    unittest.main()

