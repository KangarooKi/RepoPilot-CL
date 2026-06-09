from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class VerifierResult:
    resolved: bool
    returncode: int
    stdout: str = ""
    stderr: str = ""
    failed_tests: list[str] = field(default_factory=list)
    timeout: bool = False
    regression: bool = False
    error_summary: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def summarize_failure(stdout: str, stderr: str, max_lines: int = 20) -> str:
    lines = (stderr or stdout).strip().splitlines()
    if not lines:
        return ""
    return "\n".join(lines[-max_lines:])

