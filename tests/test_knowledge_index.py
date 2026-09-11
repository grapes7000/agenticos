import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / "chatgpt-memory" / "src" / "knowledge_index.py"
SPEC = importlib.util.spec_from_file_location("knowledge_index", SCRIPT)
assert SPEC and SPEC.loader
knowledge_index = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(knowledge_index)


class KnowledgeIndexTests(unittest.TestCase):
    def test_conversation_can_belong_to_multiple_projects_and_errors_are_normalized(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            database = base / "memory.sqlite3"
            output = base / "knowledge"
            with sqlite3.connect(database) as connection:
                connection.executescript(
                    """
                    CREATE TABLE conversations (
                      conversation_id TEXT PRIMARY KEY,title TEXT,created_at TEXT,source_file TEXT
                    );
                    CREATE TABLE analyses (
                      conversation_id TEXT PRIMARY KEY,identity TEXT,confidence REAL,
                      reasons_json TEXT,projects_json TEXT
                    );
                    CREATE TABLE project_facts (
                      source_conversation_id TEXT,project TEXT,category TEXT,statement TEXT,
                      evidence TEXT,temporal_status TEXT,confidence TEXT,source_date TEXT
                    );
                    """
                )
                connection.execute(
                    "INSERT INTO conversations VALUES(?,?,?,?)",
                    ("c1", "Fix local AI", "2026-01-01", "conversations.json"),
                )
                connection.execute(
                    "INSERT INTO analyses VALUES(?,?,?,?,?)",
                    ("c1", "LAKOTA", 0.9, json.dumps(["explicit topics"]), json.dumps(["AgenticOS", "Ollama"])),
                )
                connection.execute(
                    "INSERT INTO project_facts VALUES(?,?,?,?,?,?,?,?)",
                    ("c1", "AgenticOS", "known_issue", "Database paths diverged", "Two paths were used", "current", "HIGH", "2026-01-01"),
                )
            result = knowledge_index.build(database, output)
            with sqlite3.connect(database) as connection:
                links = connection.execute("SELECT COUNT(*) FROM conversation_projects").fetchone()[0]
                category = connection.execute("SELECT category FROM knowledge_items").fetchone()[0]
            self.assertEqual(links, 2)
            self.assertEqual(category, "error")
            self.assertEqual(result["projects"], 2)
            self.assertTrue((output / "projects" / "agenticos" / "ERROR.md").is_file())


if __name__ == "__main__":
    unittest.main()
