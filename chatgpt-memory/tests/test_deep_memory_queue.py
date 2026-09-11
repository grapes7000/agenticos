import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import deep_memory


def raw_conversation(text="AgenticOS local memory work"):
    return {
        "id": "c1",
        "current_node": "n1",
        "mapping": {
            "n1": {
                "parent": None,
                "message": {
                    "author": {"role": "user"},
                    "content": {"parts": [text]},
                },
            }
        },
    }


class DeepMemoryQueueTests(unittest.TestCase):
    def seed(self, db):
        deep_memory.ensure_schema(db)
        with deep_memory.connect(db) as con:
            con.execute(
                """INSERT INTO conversations
                   (conversation_id,title,created_at,updated_at,source_file,source_sha256,raw_json,
                    transcript,priority,state,attempts)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    "c1", "AgenticOS", "2026-09-10T00:00:00+00:00", "", "test.json", "sha",
                    json.dumps(raw_conversation()), "transcript", 0, "pending", 0,
                ),
            )
            con.execute(
                """INSERT INTO identity_classifications
                   (conversation_id,identity,confidence,reason,method,model,created_at)
                   VALUES(?,?,?,?,?,?,?)""",
                ("c1", "LAKOTA", 0.99, "test", "test", None, "now"),
            )
            con.execute(
                """INSERT INTO conversation_organizations
                   (conversation_id,identity,summary,tags_json,projects_json,conversation_type,
                    importance,model,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    "c1", "LAKOTA", "summary", "[]", '["AgenticOS"]',
                    "development", 5, "test", "now",
                ),
            )

    def test_priority_rewards_importance_projects_type_cluster_and_recency(self):
        newest = deep_memory.parse_date("2026-09-11T00:00:00+00:00")
        high = {
            "importance": 5,
            "projects_json": '["AgenticOS"]',
            "conversation_type": "development",
            "conversation_id": "high",
            "created_at": "2026-09-10T00:00:00+00:00",
            "identity": "LAKOTA",
        }
        low = {
            "importance": 1,
            "projects_json": "[]",
            "conversation_type": "general",
            "conversation_id": "low",
            "created_at": "2020-01-01T00:00:00+00:00",
            "identity": "UNKNOWN",
        }
        high_score = deep_memory.queue_priority(high, {"high"}, {"high"}, 3, newest)
        low_score = deep_memory.queue_priority(low, set(), set(), 0, newest)
        self.assertGreater(high_score, low_score)
        self.assertEqual(
            high_score,
            deep_memory.queue_priority(high, {"high"}, {"high"}, 3, newest),
        )

    def test_interrupted_processing_is_reset_to_queued(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "memory.sqlite3"
            self.seed(db)
            deep_memory.queue_conversations(db, "test-model")
            with deep_memory.connect(db) as con:
                con.execute("UPDATE deep_memory_extractions SET state='processing',claimed_at='stale'")
            deep_memory.ensure_schema(db)
            with deep_memory.connect(db) as con:
                row = con.execute("SELECT state,claimed_at FROM deep_memory_extractions").fetchone()
            self.assertEqual(row["state"], "queued")
            self.assertIsNone(row["claimed_at"])

    def test_rerun_does_not_duplicate_passage_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "memory.sqlite3"
            self.seed(db)
            deep_memory.queue_conversations(db, "test-model")
            with deep_memory.connect(db) as con:
                before = con.execute("SELECT count(*) FROM deep_memory_extractions").fetchone()[0]
            deep_memory.queue_conversations(db, "test-model")
            with deep_memory.connect(db) as con:
                after = con.execute("SELECT count(*) FROM deep_memory_extractions").fetchone()[0]
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
