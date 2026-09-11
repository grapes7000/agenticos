from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agenticos.settings import load_settings
from agenticos.workflows import collect_status


class WorkflowTests(unittest.TestCase):
    def test_status_has_stable_core_checks_without_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".git").mkdir()
            settings = load_settings(root=root, config_path=root / "missing.toml")
            with patch("agenticos.workflows._git_check") as git_check:
                from agenticos.workflows import Check

                git_check.return_value = Check("Git", "ok", "clean")
                report = collect_status(settings)
        names = {check.name for check in report.checks}
        self.assertTrue({"Disk", "Database", "Ollama", "Git", "Vault", "ChatGPT memory"} <= names)


if __name__ == "__main__":
    unittest.main()
