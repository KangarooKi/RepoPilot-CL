from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest

from repopilot.benchmark.profiles import (
    EnvironmentProfile,
    apply_environment_profile,
    load_environment_profiles,
    profile_install_repo,
)
from repopilot.benchmark.task_loader import Task


class EnvironmentProfilesTest(unittest.TestCase):
    def test_load_repo_profile_and_task_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "profiles.json"
            path.write_text(
                json.dumps(
                    {
                        "repos": {
                            "demo/repo": {
                                "setup_command": "python -m pip install -e .",
                                "install_repo": False,
                            }
                        },
                        "tasks": {
                            "demo__repo-1": {
                                "test_command": "python -m pytest tests/test_one.py",
                                "install_repo": True,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            profiles = load_environment_profiles(path)
            profile = profiles.for_task(_task("demo__repo-1"))

        self.assertEqual(profile.setup_command, "python -m pip install -e .")
        self.assertEqual(profile.test_command, "python -m pytest tests/test_one.py")
        self.assertTrue(profile.install_repo)

    def test_apply_profile_prefers_profile_setup_over_global_setup(self) -> None:
        task = _task("demo__repo-2", setup_command="task setup")
        profile = EnvironmentProfile(
            setup_command="profile setup",
            test_command="profile test",
            install_repo=False,
        )

        profiled = apply_environment_profile(
            task,
            profile,
            global_setup_command="global setup",
        )

        self.assertEqual(profiled.setup_command, "profile setup")
        self.assertEqual(profiled.test_command, "profile test")
        self.assertFalse(profile_install_repo(profile, default=True))

    def test_apply_global_setup_when_profile_has_no_setup(self) -> None:
        task = _task("demo__repo-3", setup_command="task setup")

        profiled = apply_environment_profile(
            task,
            EnvironmentProfile(),
            global_setup_command="global setup",
        )

        self.assertEqual(profiled.setup_command, "global setup")
        self.assertEqual(profiled.test_command, task.test_command)


def _task(task_id: str, setup_command: str | None = None) -> Task:
    return Task(
        task_id=task_id,
        repo="demo/repo",
        issue="Fix it.",
        test_command="python -m pytest",
        setup_command=setup_command,
    )


if __name__ == "__main__":
    unittest.main()
