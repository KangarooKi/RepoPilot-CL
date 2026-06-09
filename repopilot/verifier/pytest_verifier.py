from __future__ import annotations

from pathlib import Path

from repopilot.sandbox.runner import SandboxRunner
from repopilot.verifier.result import VerifierResult, summarize_failure


class CommandVerifier:
    """Runs a task's test command and converts output into a verifier result."""

    def __init__(self, runner: SandboxRunner, timeout_sec: int = 120) -> None:
        self.runner = runner
        self.timeout_sec = timeout_sec

    def verify(self, workdir: str | Path, command: str) -> VerifierResult:
        result = self.runner.run_command(workdir, command, timeout_sec=self.timeout_sec)
        return VerifierResult(
            resolved=result.returncode == 0 and not result.timeout,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            timeout=result.timeout,
            error_summary=summarize_failure(result.stdout, result.stderr),
        )

