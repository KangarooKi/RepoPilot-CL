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

    def __init__(
        self,
        root: str | Path = "runs",
        repo_cache_dir: str | Path | None = None,
        clone_timeout_sec: int = 600,
    ) -> None:
        self.root = Path(root)
        self.repo_cache_dir = Path(repo_cache_dir) if repo_cache_dir else None
        self.clone_timeout_sec = clone_timeout_sec

    def prepare(self, task: Task, clean: bool = True) -> Path:
        workdir = self.root / task.task_id
        if clean and workdir.exists():
            shutil.rmtree(workdir)
        workdir.mkdir(parents=True, exist_ok=True)

        if task.local_repo_path:
            self._copy_local_repo(Path(task.local_repo_path), workdir)
        elif task.repo_url:
            self._prepare_remote_repo(task, workdir)
        else:
            self._write_initial_files(task, workdir)
            self._run_git(["git", "init"], workdir)
            self._run_git(["git", "add", "."], workdir)

        if task.base_commit:
            self._run_git(["git", "checkout", task.base_commit], workdir)

        if task.test_patch:
            self._apply_test_patch(workdir, task.test_patch)

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

    @classmethod
    def _apply_test_patch(cls, workdir: Path, test_patch: str) -> None:
        normalized_patch = test_patch if test_patch.endswith("\n") else test_patch + "\n"
        completed = subprocess.run(
            ["git", "apply", "--whitespace=nowarn"],
            cwd=workdir,
            input=normalized_patch,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "Failed to apply task test_patch: "
                + (completed.stderr or completed.stdout)
            )
        cls._run_git(["git", "add", "."], workdir)
        cls._ensure_git_identity(workdir)
        cls._run_git(["git", "commit", "-m", "Apply benchmark test patch"], workdir)

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
    def _clone_repo(repo_url: str, workdir: Path, timeout_sec: int = 600) -> None:
        if workdir.exists():
            workdir.rmdir()
        subprocess.run(
            ["git", "clone", "--no-tags", repo_url, str(workdir)],
            capture_output=True,
            check=True,
            text=True,
            timeout=timeout_sec,
        )

    def _prepare_remote_repo(self, task: Task, workdir: Path) -> None:
        if self.repo_cache_dir is None:
            self._clone_repo(task.repo_url or task.repo, workdir, self.clone_timeout_sec)
            return

        self.repo_cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = self.repo_cache_dir / _cache_key(task.repo)
        if not cache_path.exists():
            temp_cache = cache_path.with_suffix(".tmp")
            if temp_cache.exists():
                shutil.rmtree(temp_cache)
            self._clone_repo(task.repo_url or task.repo, temp_cache, self.clone_timeout_sec)
            temp_cache.rename(cache_path)
        self._copy_local_repo(cache_path, workdir)

    @staticmethod
    def _ensure_git_identity(workdir: Path) -> None:
        subprocess.run(
            ["git", "config", "user.name", "RepoPilot"],
            cwd=workdir,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "repopilot@example.com"],
            cwd=workdir,
            capture_output=True,
            check=True,
        )


def _cache_key(repo: str) -> str:
    return repo.replace("/", "__").replace(":", "_")
