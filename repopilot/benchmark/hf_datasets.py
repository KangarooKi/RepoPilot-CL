from __future__ import annotations

import json
import ssl
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode

try:
    import certifi
except ImportError:  # pragma: no cover - optional runtime dependency
    certifi = None


HF_ROWS_ENDPOINT = "https://datasets-server.huggingface.co/rows"


@dataclass(frozen=True)
class HFDatasetRowsRequest:
    dataset: str
    config: str = "default"
    split: str = "dev"
    offset: int = 0
    length: int = 5

    def url(self) -> str:
        query = urlencode(
            {
                "dataset": self.dataset,
                "config": self.config,
                "split": self.split,
                "offset": self.offset,
                "length": self.length,
            }
        )
        return f"{HF_ROWS_ENDPOINT}?{query}"


def fetch_rows(request: HFDatasetRowsRequest) -> list[dict[str, object]]:
    http_request = urllib.request.Request(request.url(), method="GET")
    with urllib.request.urlopen(http_request, context=_ssl_context(), timeout=120) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return [row["row"] for row in payload.get("rows", [])]


def write_jsonl(records: list[dict[str, object]], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return output


def _ssl_context() -> ssl.SSLContext:
    if certifi is not None:
        return ssl.create_default_context(cafile=certifi.where())
    return ssl.create_default_context()

