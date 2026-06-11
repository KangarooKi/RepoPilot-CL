from __future__ import annotations

import os
import shutil
import subprocess
import sys
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
        use_venv: bool = False,
        venv_root: str | Path | None = None,
        python_executable: str | Path | None = None,
        install_repo: bool = False,
    ) -> None:
        self.root = Path(root).resolve()
        self.repo_cache_dir = Path(repo_cache_dir).resolve() if repo_cache_dir else None
        self.clone_timeout_sec = clone_timeout_sec
        self.use_venv = use_venv
        self.venv_root = Path(venv_root).resolve() if venv_root else self.root / ".venvs"
        self.python_executable = str(python_executable or sys.executable)
        self.install_repo = install_repo
        self._venvs_by_workdir: dict[Path, Path] = {}

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

        if self.use_venv:
            self._prepare_venv(task, workdir, clean=clean)

        if self.install_repo:
            install = self.run_command(
                workdir,
                "python -m pip install -e .",
                timeout_sec=900,
            )
            if install.returncode != 0:
                raise RuntimeError(
                    f"Repo install failed for {task.task_id}: "
                    + (install.stderr or install.stdout)
                )

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
            workdir_path = Path(workdir)
            completed = subprocess.run(
                command,
                cwd=workdir_path,
                shell=True,
                text=True,
                capture_output=True,
                timeout=timeout_sec,
                check=False,
                env=self._command_env(workdir_path),
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

    def replace_text(
        self,
        workdir: str | Path,
        relative_path: str,
        old: str,
        new: str,
    ) -> CommandResult:
        if not old:
            return CommandResult(
                command=f"replace_text {relative_path}",
                returncode=2,
                stdout="",
                stderr="Replacement target `old` must not be empty.",
            )

        try:
            content = self.read_file(workdir, relative_path)
        except OSError as exc:
            return CommandResult(
                command=f"replace_text {relative_path}",
                returncode=1,
                stdout="",
                stderr=str(exc),
            )

        matches = content.count(old)
        if matches != 1:
            return CommandResult(
                command=f"replace_text {relative_path}",
                returncode=1,
                stdout="",
                stderr=f"Expected exactly one match for `old`, found {matches}.",
            )

        self.write_file(workdir, relative_path, content.replace(old, new, 1))
        return CommandResult(
            command=f"replace_text {relative_path}",
            returncode=0,
            stdout=f"Replaced one occurrence in {relative_path}.",
            stderr="",
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

    def _prepare_venv(self, task: Task, workdir: Path, clean: bool) -> Path:
        venv_dir = self.venv_root / _cache_key(task.task_id)
        if clean and venv_dir.exists():
            shutil.rmtree(venv_dir)
        if not venv_dir.exists():
            venv_dir.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                [self.python_executable, "-m", "venv", str(venv_dir)],
                cwd=workdir,
                capture_output=True,
                check=True,
                text=True,
            )
        self._venvs_by_workdir[workdir.resolve()] = venv_dir.resolve()
        return venv_dir

    def _command_env(self, workdir: Path) -> dict[str, str]:
        env = os.environ.copy()
        venv_dir = self._venvs_by_workdir.get(workdir.resolve())
        if venv_dir is None:
            return env

        bin_dir = venv_dir / ("Scripts" if os.name == "nt" else "bin")
        env["VIRTUAL_ENV"] = str(venv_dir)
        env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
        return env

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
