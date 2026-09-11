from pathlib import Path
import sqlite3
import tempfile
import unittest

from agenticos.database import initialize_database


class DatabaseTests(unittest.TestCase):
    def test_schema_initialization_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "agentos.sqlite3"
            initialize_database(path)
            initialize_database(path)
            with sqlite3.connect(path) as connection:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
                version = connection.execute(
                    "SELECT value FROM settings WHERE key='schema_version'"
                ).fetchone()[0]
        self.assertTrue({"files", "actions", "lessons", "runs", "events"} <= tables)
        self.assertEqual(version, "3")


if __name__ == "__main__":
    unittest.main()
