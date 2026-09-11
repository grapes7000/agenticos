import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from chatgpt_memory import connect, init_database  # noqa: E402
from identify_fast import (  # noqa: E402
    ensure_identity_schema,
    identify,
    normalize_identity,
    sampled_user_excerpt,
)


def conversation(messages):
    mapping = {}
    parent = None
    for i, text in enumerate(messages):
        node = f"m{i}"
        mapping[node] = {
            "parent": parent,
            "message": {
                "id": node,
                "author": {"role": "user"},
                "content": {"parts": [text]},
            },
        }
        parent = node
    return {"current_node": parent, "mapping": mapping}


class FastIdentityTests(unittest.TestCase):
    def test_excerpt_samples_long_conversation(self):
        conv = conversation([f"message {i} " + ("x" * 1200) for i in range(10)])
        excerpt = sampled_user_excerpt(conv, max_chars=4500)
        self.assertLessEqual(len(excerpt), 4500)
        self.assertIn("message 0", excerpt)
        self.assertIn("message 9", excerpt)

    def test_normalize_identity_rejects_invalid_label(self):
        with self.assertRaises(ValueError):
            normalize_identity({"identity": "OTHER", "confidence": 1, "reason": "bad"})

    def test_obvious_lakota_chat_skips_llm(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "memory.sqlite3"
            init_database(db)
            ensure_identity_schema(db)
            conv = conversation(["I need help with tailscale ssh on my linux server"])
            with connect(db) as con:
                con.execute(
                    """INSERT INTO conversations
                       (conversation_id,title,created_at,updated_at,source_file,source_sha256,raw_json,transcript,priority,state,attempts)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        "c1",
                        "Tailscale SSH Setup Guide",
                        "2026-01-01",
                        "2026-01-01",
                        "test.json",
                        "sha",
                        json.dumps(conv),
                        "tailscale ssh linux server",
                        100,
                        "pending",
                        0,
                    ),
                )

            with patch("identify_fast.ollama_identity") as llm:
                result = identify(db, limit=1, model="test", host="localhost:11434")

            llm.assert_not_called()
            self.assertEqual(result["deterministic"], 1)
            with connect(db) as con:
                row = con.execute(
                    "SELECT identity,method FROM identity_classifications WHERE conversation_id='c1'"
                ).fetchone()
            self.assertEqual(tuple(row), ("LAKOTA", "deterministic"))


if __name__ == "__main__":
    unittest.main()
