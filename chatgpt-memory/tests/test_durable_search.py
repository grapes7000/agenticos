import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "chatgpt-memory" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import deep_memory
import deep_memory_finalize as finalize

spec = importlib.util.spec_from_file_location("search_memory", ROOT / "tools" / "search_memory.py")
search_memory = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(search_memory)


class DurableSearchTests(unittest.TestCase):
    def test_durable_group_is_loaded_and_preferred_for_keyword_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "memory.sqlite3"
            finalize.ensure_finalize_schema(db)
            with deep_memory.connect(db) as con:
                con.execute(
                    """INSERT INTO conversations
                       (conversation_id,title,created_at,updated_at,source_file,source_sha256,raw_json,
                        transcript,priority,state,attempts)
                       VALUES('c1','AgenticOS','2026-09-11','','test','sha','{}','',0,'pending',0)"""
                )
                con.execute("INSERT INTO projects(slug,name,updated_at) VALUES('agenticos','AgenticOS','now')")
                con.execute(
                    """INSERT INTO knowledge_items
                       (fingerprint,project_slug,category,title,statement,evidence,status,confidence,
                        source_conversation_id,source_date,created_at,namespace,origin)
                       VALUES('fp','agenticos','configuration','','AgenticOS uses SQLite for canonical memory.',
                              'The user confirmed SQLite is canonical.','current','0.95','c1','2026-09-11','now','lakota','stage3')"""
                )
                item_id = con.execute("SELECT id FROM knowledge_items WHERE fingerprint='fp'").fetchone()[0]
                con.execute(
                    "INSERT INTO knowledge_item_projects VALUES(?, 'agenticos', 1.0, 'stage3')", (item_id,)
                )
            finalize.build_groups(db)

            old_chat_db = search_memory.CHAT_DB
            old_db = search_memory.DB
            try:
                search_memory.CHAT_DB = db
                search_memory.DB = Path(tmp) / "missing.sqlite3"
                rows = search_memory.load_durable()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["source_type"], "durable")
                with mock.patch.object(search_memory, "embed", return_value=None):
                    results = search_memory.search("SQLite canonical memory", limit=5, include={"durable"})
                self.assertEqual(results[0]["source_type"], "durable")
                self.assertGreater(results[0]["score"], 12)
            finally:
                search_memory.CHAT_DB = old_chat_db
                search_memory.DB = old_db


if __name__ == "__main__":
    unittest.main()
