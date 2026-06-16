from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import json
import re
from pathlib import Path
from typing import Any

from repopilot.critic.failure import FailureHint, render_failure_hints_markdown


CRITIC_KEYS = ("failure_type", "focus_files", "suggested_queries", "avoid", "next_steps")


@dataclass(frozen=True)
class CriticParseResult:
    prediction: dict[str, object]
    valid_json: bool
    schema_valid: bool
    error: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CriticEvalSummary:
    examples: int
    valid_json: int
    schema_valid: int
    failure_type_total: int
    failure_type_correct: int
    focus_total: int
    focus_hits: dict[str, int]
    focus_mrr_sum: float
    query_nonempty: int
    next_steps_nonempty: int
    missing_reference: int
    invalid_failure_types: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["valid_json_rate"] = _safe_div(self.valid_json, self.examples)
        payload["schema_valid_rate"] = _safe_div(self.schema_valid, self.examples)
        payload["failure_type_accuracy"] = _safe_div(
            self.failure_type_correct,
            self.failure_type_total,
        )
        payload["query_nonempty_rate"] = _safe_div(self.query_nonempty, self.examples)
        payload["next_steps_nonempty_rate"] = _safe_div(
            self.next_steps_nonempty,
            self.examples,
        )
        payload["focus_recall"] = {
            key: _safe_div(value, self.focus_total)
            for key, value in self.focus_hits.items()
        }
        payload["focus_mrr"] = (
            self.focus_mrr_sum / float(self.focus_total)
            if self.focus_total
            else 0.0
        )
        return payload


def parse_critic_output(text: str) -> CriticParseResult:
    candidate = _extract_json_text(text)
    if not candidate:
        return CriticParseResult(
            prediction=_empty_prediction(),
            valid_json=False,
            schema_valid=False,
            error="no_json_object",
        )
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as exc:
        return CriticParseResult(
            prediction=_empty_prediction(),
            valid_json=False,
            schema_valid=False,
            error=f"json_decode_error:{exc.msg}",
        )
    if not isinstance(payload, dict):
        return CriticParseResult(
            prediction=_empty_prediction(),
            valid_json=False,
            schema_valid=False,
            error="json_not_object",
        )
    prediction = normalize_critic_payload(payload)
    schema_valid = is_schema_valid(payload)
    return CriticParseResult(
        prediction=prediction,
        valid_json=True,
        schema_valid=schema_valid,
        error="" if schema_valid else "schema_invalid",
    )


def normalize_critic_payload(payload: dict[str, Any]) -> dict[str, object]:
    return {
        "failure_type": _clean_scalar(payload.get("failure_type", "")),
        "focus_files": _clean_list(payload.get("focus_files", []), path_like=True),
        "suggested_queries": _clean_list(payload.get("suggested_queries", [])),
        "avoid": _clean_list(payload.get("avoid", [])),
        "next_steps": _clean_list(payload.get("next_steps", [])),
    }


def is_schema_valid(payload: dict[str, Any]) -> bool:
    if any(key not in payload for key in CRITIC_KEYS):
        return False
    if not isinstance(payload.get("failure_type"), str):
        return False
    for key in CRITIC_KEYS[1:]:
        if not isinstance(payload.get(key), list):
            return False
    return True


def prediction_to_failure_hint(row: dict[str, Any]) -> FailureHint:
    prediction = normalize_critic_payload(_coerce_prediction(row.get("prediction", {})))
    return FailureHint(
        task_id=str(row.get("task_id", "")),
        repo=str(row.get("repo", "")),
        failure_type=str(prediction["failure_type"]),
        issue_title=str(row.get("issue_title", "")),
        baseline_error=str(row.get("baseline_error", "")),
        last_failure=str(row.get("last_failure", "")),
        focus_files=[str(item) for item in prediction["focus_files"]],
        suggested_queries=[str(item) for item in prediction["suggested_queries"]],
        avoid=[str(item) for item in prediction["avoid"]],
        next_steps=[str(item) for item in prediction["next_steps"]],
    )


def write_learned_failure_hints(
    prediction_rows: list[dict[str, Any]],
    output_json: str | Path,
    *,
    output_md: str | Path | None = None,
    title: str = "Learned Critic Hints",
    include_invalid: bool = False,
) -> list[FailureHint]:
    hints = []
    for row in prediction_rows:
        if not include_invalid and not bool(row.get("schema_valid", False)):
            continue
        hint = prediction_to_failure_hint(row)
        if hint.task_id:
            hints.append(hint)
    output_json = Path(output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(
            {
                "source": "learned_critic_lora",
                "hints": [hint.to_dict() for hint in hints],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    if output_md is not None:
        output_md = Path(output_md)
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(
            render_failure_hints_markdown(hints, title=title, source=output_json),
            encoding="utf-8",
        )
    return hints


def load_jsonl(path: str | Path, *, max_examples: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                rows.append(payload)
            if max_examples is not None and len(rows) >= max_examples:
                break
    return rows


def reference_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, object]]:
    refs: dict[str, dict[str, object]] = {}
    for row in rows:
        target = row.get("target") or row.get("reference")
        if not isinstance(target, dict):
            continue
        normalized = normalize_critic_payload(target)
        for key in _row_keys(row):
            refs[key] = normalized
    return refs


def evaluate_predictions(
    prediction_rows: list[dict[str, Any]],
    *,
    references: dict[str, dict[str, object]] | None = None,
    focus_ks: tuple[int, ...] = (1, 3, 5),
) -> CriticEvalSummary:
    references = references or {}
    focus_hits = {f"recall@{k}": 0 for k in focus_ks}
    invalid_failure_types: Counter[str] = Counter()
    valid_json = 0
    schema_valid = 0
    failure_type_total = 0
    failure_type_correct = 0
    focus_total = 0
    focus_mrr_sum = 0.0
    query_nonempty = 0
    next_steps_nonempty = 0
    missing_reference = 0

    for row in prediction_rows:
        valid_json += int(bool(row.get("valid_json", True)))
        schema_valid += int(bool(row.get("schema_valid", False)))
        prediction = normalize_critic_payload(_coerce_prediction(row.get("prediction", {})))
        failure_type = str(prediction.get("failure_type", ""))
        if failure_type and not _valid_failure_type(failure_type):
            invalid_failure_types[failure_type] += 1
        query_nonempty += int(bool(prediction["suggested_queries"]))
        next_steps_nonempty += int(bool(prediction["next_steps"]))

        reference = _row_reference(row, references)
        if reference is None:
            missing_reference += 1
            continue
        ref_failure = str(reference.get("failure_type", ""))
        if ref_failure:
            failure_type_total += 1
            failure_type_correct += int(failure_type == ref_failure)
        ref_focus = _normalize_paths(reference.get("focus_files", []))
        pred_focus = _normalize_paths(prediction.get("focus_files", []))
        if ref_focus:
            focus_total += 1
            rank = _first_relevant_rank(pred_focus, ref_focus)
            if rank is not None:
                focus_mrr_sum += 1.0 / float(rank)
            for key, k in zip(focus_hits, focus_ks):
                focus_hits[key] += int(bool(set(pred_focus[:k]) & set(ref_focus)))

    return CriticEvalSummary(
        examples=len(prediction_rows),
        valid_json=valid_json,
        schema_valid=schema_valid,
        failure_type_total=failure_type_total,
        failure_type_correct=failure_type_correct,
        focus_total=focus_total,
        focus_hits=focus_hits,
        focus_mrr_sum=focus_mrr_sum,
        query_nonempty=query_nonempty,
        next_steps_nonempty=next_steps_nonempty,
        missing_reference=missing_reference,
        invalid_failure_types=dict(sorted(invalid_failure_types.items())),
    )


def render_eval_markdown(
    summary: CriticEvalSummary,
    *,
    title: str = "Learned Critic Evaluation",
    source: str | Path | None = None,
) -> str:
    payload = summary.to_dict()
    lines = [f"# {title}", ""]
    if source is not None:
        lines.extend([f"- Source: `{source}`", ""])
    lines.extend(
        [
            "| Metric | Value |",
            "|---|---:|",
            f"| Examples | {summary.examples} |",
            f"| Valid JSON | {summary.valid_json} ({payload['valid_json_rate']:.3f}) |",
            f"| Schema Valid | {summary.schema_valid} ({payload['schema_valid_rate']:.3f}) |",
            (
                f"| Failure Type Accuracy | {summary.failure_type_correct}/"
                f"{summary.failure_type_total} ({payload['failure_type_accuracy']:.3f}) |"
            ),
            f"| Query Nonempty | {summary.query_nonempty} ({payload['query_nonempty_rate']:.3f}) |",
            (
                f"| Next Steps Nonempty | {summary.next_steps_nonempty} "
                f"({payload['next_steps_nonempty_rate']:.3f}) |"
            ),
            f"| Missing Reference | {summary.missing_reference} |",
            f"| Focus MRR | {payload['focus_mrr']:.3f} |",
        ]
    )
    focus_recall = payload["focus_recall"]
    if isinstance(focus_recall, dict):
        for key, value in focus_recall.items():
            lines.append(f"| Focus {key} | {summary.focus_hits[key]}/{summary.focus_total} ({value:.3f}) |")
    if summary.invalid_failure_types:
        lines.extend(["", "Invalid failure types:", ""])
        lines.extend(
            f"- `{failure_type}`: {count}"
            for failure_type, count in summary.invalid_failure_types.items()
        )
    return "\n".join(lines).rstrip() + "\n"


def _extract_json_text(text: str) -> str:
    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", stripped, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        stripped = fenced.group(1).strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    start = stripped.find("{")
    if start < 0:
        return ""
    depth = 0
    in_string = False
    escape = False
    for offset, char in enumerate(stripped[start:], start=start):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return stripped[start : offset + 1]
    return ""


def _row_reference(
    row: dict[str, Any],
    references: dict[str, dict[str, object]],
) -> dict[str, object] | None:
    reference = row.get("reference") or row.get("target")
    if isinstance(reference, dict):
        return normalize_critic_payload(reference)
    for key in _row_keys(row):
        if key in references:
            return references[key]
    return None


def _row_keys(row: dict[str, Any]) -> list[str]:
    keys = []
    for field in ("example_id", "task_id"):
        value = str(row.get(field, "")).strip()
        if value:
            keys.append(value)
    return keys


def _coerce_prediction(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _empty_prediction() -> dict[str, object]:
    return normalize_critic_payload({})


def _clean_scalar(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _clean_list(value: object, *, path_like: bool = False) -> list[str]:
    if isinstance(value, str):
        items: list[object] = [value]
    elif isinstance(value, list):
        items = value
    else:
        items = []
    cleaned = []
    seen = set()
    for item in items:
        text = _clean_scalar(item)
        if path_like:
            text = _normalize_path(text)
        if not text or text in seen:
            continue
        cleaned.append(text)
        seen.add(text)
    return cleaned


def _normalize_paths(value: object) -> list[str]:
    return _clean_list(value, path_like=True)


def _normalize_path(path: str) -> str:
    normalized = path.strip().replace("\\", "/")
    if normalized.startswith("a/") or normalized.startswith("b/"):
        normalized = normalized[2:]
    normalized = re.sub(r"/+", "/", normalized)
    return normalized.strip("/")


def _first_relevant_rank(predicted: list[str], reference: list[str]) -> int | None:
    reference_set = set(reference)
    for index, path in enumerate(predicted, start=1):
        if path in reference_set:
            return index
    return None


def _valid_failure_type(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z][a-z0-9_]*", value))


def _safe_div(numerator: int, denominator: int) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0
