from pathlib import Path
import tempfile
import unittest

from agenticos.settings import load_settings


class SettingsTests(unittest.TestCase):
    def test_defaults_are_rooted_outside_repository_data(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = load_settings(root=Path(directory), config_path=Path(directory) / "missing.toml")
        self.assertEqual(settings.root, Path(directory).resolve())
        self.assertEqual(settings.database_path.name, "agentos.sqlite3")
        self.assertNotEqual(settings.database_path.parent, settings.root / "data")

    def test_toml_values_expand_home(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config.toml"
            config.write_text('[agenticos]\nvault="~/vault-test"\nmodel="tiny"\n', encoding="utf-8")
            settings = load_settings(root=root, config_path=config)
        self.assertEqual(settings.model, "tiny")
        self.assertEqual(settings.vault, Path.home() / "vault-test")


if __name__ == "__main__":
    unittest.main()
