import unittest

from repopilot.agent.actions import parse_action


class ActionsTest(unittest.TestCase):
    def test_parse_action_from_json_fence(self) -> None:
        action = parse_action(
            """```json
{"action": "read_file", "args": {"path": "calc.py"}, "thought": "inspect"}
```"""
        )

        self.assertEqual(action.name, "read_file")
        self.assertEqual(action.args["path"], "calc.py")
        self.assertEqual(action.thought, "inspect")

    def test_reject_unsupported_action(self) -> None:
        with self.assertRaises(ValueError):
            parse_action('{"action": "delete_repo", "args": {}}')


if __name__ == "__main__":
    unittest.main()

