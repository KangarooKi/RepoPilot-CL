from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path
from typing import Any

from repopilot.benchmark.task_loader import Task


@dataclass(frozen=True)
class EnvironmentProfile:
    setup_command: str | None = None
    test_command: str | None = None
    install_repo: bool | None = None


@dataclass(frozen=True)
class EnvironmentProfiles:
    repos: dict[str, EnvironmentProfile]
    tasks: dict[str, EnvironmentProfile]

    @classmethod
    def empty(cls) -> "EnvironmentProfiles":
        return cls(repos={}, tasks={})

    def for_task(self, task: Task) -> EnvironmentProfile:
        repo_profile = self.repos.get(task.repo, EnvironmentProfile())
        task_profile = self.tasks.get(task.task_id, EnvironmentProfile())
        return EnvironmentProfile(
            setup_command=task_profile.setup_command or repo_profile.setup_command,
            test_command=task_profile.test_command or repo_profile.test_command,
            install_repo=(
                task_profile.install_repo
                if task_profile.install_repo is not None
                else repo_profile.install_repo
            ),
        )


def load_environment_profiles(path: str | Path | None) -> EnvironmentProfiles:
    if path is None:
        return EnvironmentProfiles.empty()
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return EnvironmentProfiles(
        repos=_load_profile_map(payload.get("repos", {})),
        tasks=_load_profile_map(payload.get("tasks", {})),
    )


def apply_environment_profile(
    task: Task,
    profile: EnvironmentProfile,
    *,
    global_setup_command: str | None = None,
) -> Task:
    setup_command = global_setup_command if global_setup_command is not None else task.setup_command
    if profile.setup_command is not None:
        setup_command = profile.setup_command
    test_command = profile.test_command or task.test_command
    if setup_command == task.setup_command and test_command == task.test_command:
        return task
    return replace(task, setup_command=setup_command, test_command=test_command)


def profile_install_repo(
    profile: EnvironmentProfile,
    *,
    default: bool,
) -> bool:
    return default if profile.install_repo is None else profile.install_repo


def _load_profile_map(raw: object) -> dict[str, EnvironmentProfile]:
    if not isinstance(raw, dict):
        return {}
    profiles: dict[str, EnvironmentProfile] = {}
    for key, value in raw.items():
        if isinstance(value, dict):
            profiles[str(key)] = _profile_from_dict(value)
    return profiles


def _profile_from_dict(payload: dict[str, Any]) -> EnvironmentProfile:
    return EnvironmentProfile(
        setup_command=_optional_string(payload.get("setup_command")),
        test_command=_optional_string(payload.get("test_command")),
        install_repo=_optional_bool(payload.get("install_repo")),
    )


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _optional_bool(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return bool(value)
