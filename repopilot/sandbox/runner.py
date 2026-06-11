from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from repopilot.benchmark.task_loader import Task


@dataclass(frozen=True)
class CommandResult:
    command: str
    returncode: int
    stdout: str
    stderr: str
    timeout: bool = False


class SandboxRunner:
    """Creates an isolated working tree for one repair task."""

    def __init__(self, root: str | Path = "runs") -> None:
        self.root = Path(root)

    def prepare(self, task: Task, clean: bool = True) -> Path:
        workdir = self.root / task.task_id
        if clean and workdir.exists():
            shutil.rmtree(workdir)
        workdir.mkdir(parents=True, exist_ok=True)

        for relative_path, content in task.initial_files.items():
            destination = workdir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")

        self._run_git(["git", "init"], workdir)
        self._run_git(["git", "add", "."], workdir)
        return workdir

    def run_command(
        self,
        workdir: str | Path,
        command: str,
        timeout_sec: int = 120,
    ) -> CommandResult:
        try:
            completed = subprocess.run(
                command,
                cwd=Path(workdir),
                shell=True,
                text=True,
                capture_output=True,
                timeout=timeout_sec,
                check=False,
            )
            return CommandResult(
                command=command,
                returncode=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        except subprocess.TimeoutExpired as exc:
            return CommandResult(
                command=command,
                returncode=124,
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
                timeout=True,
            )

    def apply_unified_diff(self, workdir: str | Path, diff: str) -> CommandResult:
        normalized_diff = diff if diff.endswith("\n") else diff + "\n"
        completed = subprocess.run(
            ["git", "apply", "--whitespace=nowarn"],
            cwd=Path(workdir),
            input=normalized_diff,
            text=True,
            capture_output=True,
            check=False,
        )
        return CommandResult(
            command="git apply --whitespace=nowarn",
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def git_diff(self, workdir: str | Path) -> str:
        completed = subprocess.run(
            ["git", "diff", "--no-ext-diff"],
            cwd=Path(workdir),
            text=True,
            capture_output=True,
            check=False,
        )
        return completed.stdout

    def read_file(self, workdir: str | Path, relative_path: str) -> str:
        return (Path(workdir) / relative_path).read_text(encoding="utf-8")

    def write_file(self, workdir: str | Path, relative_path: str, content: str) -> None:
        path = Path(workdir) / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    @staticmethod
    def _run_git(args: list[str], workdir: Path) -> None:
        subprocess.run(args, cwd=workdir, capture_output=True, check=True)
