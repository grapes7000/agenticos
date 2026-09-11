import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

spec = importlib.util.spec_from_file_location("organize_fast", SRC / "organize_fast.py")
organize_fast = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(organize_fast)


class OrganizeFastTests(unittest.TestCase):
    def test_normalize_preserves_deterministic_projects(self):
        result = organize_fast.normalize_result(
            {
                "summary": "Configure remote SSH access over Tailscale.",
                "tags": ["ssh", "tailscale", "linux"],
                "projects": [],
                "conversation_type": "setup_configuration",
                "importance": 4,
            },
            "Tailscale SSH Setup Guide",
            ["Homelab-Self-Hosting"],
        )
        self.assertEqual(result["conversation_type"], "setup_configuration")
        self.assertEqual(result["importance"], 4)
        self.assertIn("Homelab-Self-Hosting", result["projects"])

    def test_organize_uses_existing_identity_without_reclassification(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "memory.sqlite3"
            organize_fast.ensure_schema(db)
            raw = {
                "id": "c1",
                "current_node": "n1",
                "mapping": {
                    "n1": {
                        "parent": None,
                        "message": {
                            "author": {"role": "user"},
                            "content": {"parts": ["Help me configure SSH over Tailscale on my Linux server."]},
                        },
                    }
                },
            }
            with organize_fast.connect(db) as con:
                con.execute(
                    """INSERT INTO conversations
                       (conversation_id,title,created_at,updated_at,source_file,source_sha256,raw_json,transcript,priority,state,attempts)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        "c1",
                        "Tailscale SSH Setup Guide",
                        "",
                        "",
                        "test.json",
                        "sha",
                        json.dumps(raw),
                        "[user] Help me configure SSH over Tailscale on my Linux server.",
                        0,
                        "pending",
                        0,
                    ),
                )
                con.execute(
                    """INSERT INTO identity_classifications
                       (conversation_id,identity,confidence,reason,method,model,created_at)
                       VALUES(?,?,?,?,?,?,?)""",
                    ("c1", "LAKOTA", 0.98, "technical signals", "deterministic", None, "now"),
                )

            fake = {
                "summary": "Set up SSH access to a Linux server through Tailscale.",
                "tags": ["ssh", "tailscale", "linux"],
                "projects": ["Homelab-Self-Hosting"],
                "conversation_type": "setup_configuration",
                "importance": 4,
            }
            with mock.patch.object(organize_fast, "ollama_organize", return_value=fake) as mocked:
                stats = organize_fast.organize(db, 10, "test-model", "127.0.0.1:11434")

            self.assertEqual(stats["processed"], 1)
            mocked.assert_called_once()
            args = mocked.call_args.args
            self.assertEqual(args[1], "LAKOTA")
            with organize_fast.connect(db) as con:
                row = con.execute(
                    "SELECT identity,conversation_type,importance FROM conversation_organizations WHERE conversation_id='c1'"
                ).fetchone()
            self.assertEqual(row["identity"], "LAKOTA")
            self.assertEqual(row["conversation_type"], "setup_configuration")
            self.assertEqual(row["importance"], 4)


if __name__ == "__main__":
    unittest.main()
