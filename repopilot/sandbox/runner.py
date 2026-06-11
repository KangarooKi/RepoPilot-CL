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

        if task.local_repo_path:
            self._copy_local_repo(Path(task.local_repo_path), workdir)
        elif task.repo_url:
            self._clone_repo(task.repo_url, workdir)
        else:
            self._write_initial_files(task, workdir)
            self._run_git(["git", "init"], workdir)
            self._run_git(["git", "add", "."], workdir)

        if task.base_commit:
            self._run_git(["git", "checkout", task.base_commit], workdir)

        if task.setup_command:
            setup = self.run_command(workdir, task.setup_command, timeout_sec=600)
            if setup.returncode != 0:
                raise RuntimeError(
                    f"Setup command failed for {task.task_id}: {setup.stderr or setup.stdout}"
                )
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

    @staticmethod
    def _write_initial_files(task: Task, workdir: Path) -> None:
        for relative_path, content in task.initial_files.items():
            destination = workdir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")

    @staticmethod
    def _copy_local_repo(source: Path, workdir: Path) -> None:
        if not source.exists():
            raise FileNotFoundError(f"Local repo path does not exist: {source}")
        for item in source.iterdir():
            destination = workdir / item.name
            if item.is_dir():
                shutil.copytree(item, destination)
            else:
                shutil.copy2(item, destination)

    @staticmethod
    def _clone_repo(repo_url: str, workdir: Path) -> None:
        workdir.rmdir()
        subprocess.run(
            ["git", "clone", "--no-tags", repo_url, str(workdir)],
            capture_output=True,
            check=True,
            text=True,
        )
