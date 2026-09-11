import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from chatgpt_memory import (  # noqa: E402
    classify_keywords,
    flatten_conversation,
    init_database,
    ingest_export,
    claim_next,
    record_result,
    record_deep_result,
    search_memory,
    render_views,
    deepen,
    source_conversation,
    record_project_facts,
    render_project_documents,
)


class PipelineTests(unittest.TestCase):
    def test_flatten_uses_active_branch_in_time_order(self):
        conversation = {
            "id": "conv-1", "title": "Test", "create_time": 10,
            "current_node": "a2",
            "mapping": {
                "root": {"parent": None, "message": None},
                "u1": {"parent": "root", "message": {"create_time": 12, "author": {"role": "user"}, "content": {"parts": ["hello"]}}},
                "a1": {"parent": "u1", "message": {"create_time": 13, "author": {"role": "assistant"}, "content": {"parts": ["hi"]}}},
                "a2": {"parent": "a1", "message": {"create_time": 14, "author": {"role": "user"}, "content": {"parts": ["linux mint docker"]}}},
                "orphan": {"parent": "root", "message": {"create_time": 11, "author": {"role": "user"}, "content": {"parts": ["wrong branch"]}}},
            },
        }
        messages = flatten_conversation(conversation)
        self.assertEqual([m["text"] for m in messages], ["hello", "hi", "linux mint docker"])

    def test_keyword_classification_is_conservative_and_records_signals(self):
        label, confidence, reasons = classify_keywords("Docker, Tailscale, and SSH on Linux Mint")
        self.assertEqual(label, "LAKOTA")
        self.assertGreaterEqual(confidence, 0.80)
        self.assertTrue(reasons)
        label, confidence, _ = classify_keywords("make a glittery angel character with wings")
        self.assertEqual(label, "BROOKE")
        self.assertGreaterEqual(confidence, 0.80)
        label, confidence, _ = classify_keywords("hello there")
        self.assertEqual(label, "UNKNOWN")
        self.assertLessEqual(confidence, 0.50)

    def test_brooke_image_generation_with_emo_character_is_strongly_classified(self):
        label, confidence, reasons = classify_keywords("Emo Girl Fortnite Image: create an image of an emo girl")
        self.assertEqual(label, "BROOKE")
        self.assertGreaterEqual(confidence, 0.80)
        self.assertTrue(reasons)

    def test_database_ingestion_and_claim_are_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "export"
            source.mkdir()
            conversation = {
                "id": "conv-1", "title": "Hermes Docker", "create_time": 100,
                "update_time": 101, "current_node": "u1",
                "mapping": {"u1": {"parent": None, "message": {"create_time": 100, "author": {"role": "user"}, "content": {"parts": ["Set up Hermes with Docker"]}}}},
            }
            (source / "conversations-000.json").write_text(json.dumps([conversation]))
            db = root / "memory.sqlite3"
            init_database(db)
            self.assertEqual(ingest_export(db, source), 1)
            self.assertEqual(ingest_export(db, source), 0)
            row = claim_next(db)
            self.assertEqual(row["conversation_id"], "conv-1")
            record_result(db, "conv-1", {"identity": "LAKOTA", "confidence": 0.95, "reasons": ["technical signals"], "summary": "test", "tags": ["docker"], "projects": ["Hermes"], "memories": []})
            opened = source_conversation(db, "conv-1")
            self.assertEqual(opened["source_file"], str(source / "conversations-000.json"))
            self.assertIn("Set up Hermes with Docker", opened["transcript"])
            self.assertIsNone(claim_next(db))

    def test_deep_facts_preserve_provenance_and_search_durable_memory_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "memory.sqlite3"
            init_database(db)
            with __import__("sqlite3").connect(db) as con:
                con.execute("""INSERT INTO conversations(conversation_id,title,created_at,updated_at,source_file,source_sha256,raw_json,transcript,state)
                               VALUES(?,?,?,?,?,?,?,?,?)""", ("conv-42", "Hermes Gateway", "2026-01-02T00:00:00+00:00", "", "/export/conversations-000.json", "abc", "{}", "[user] configure Hermes gateway", "done"))
                con.execute("""INSERT INTO analyses VALUES(?,?,?,?,?,?,?,?,?,?)""", ("conv-42", "LAKOTA", .95, "[]", "Gateway setup", "[]", '["Hermes"]', "{}", "qwen2.5:7b-instruct", "2026-01-02T00:00:00+00:00"))
            record_deep_result(db, "conv-42", {"facts": [{"project": "Hermes", "category": "architecture_decision", "statement": "Gateway access stays localhost-only behind Tailscale.", "evidence": "Use Tailscale rather than public exposure.", "confidence": "HIGH"}]}, "qwen2.5:7b-instruct")
            rows = search_memory(db, "Hermes gateway Tailscale", limit=5)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["layer"], "durable")
            self.assertEqual(rows[0]["conversation_id"], "conv-42")
            self.assertEqual(rows[0]["source_file"], "/export/conversations-000.json")
            render_views(db, root, "test", "qwen2.5:7b-instruct")
            project_doc = root / "memory" / "lakota" / "knowledge" / "Hermes.md"
            self.assertIn("Gateway access stays localhost-only", project_doc.read_text())
            self.assertIn("conversation_id=conv-42", project_doc.read_text())
            with __import__("sqlite3").connect(db) as con:
                self.assertEqual(con.execute("select count(*) from deep_facts where source_conversation_id='conv-42' and identity='LAKOTA'").fetchone()[0], 1)

    def test_project_expansion_renders_cited_structured_documents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); db = root / "memory.sqlite3"; init_database(db)
            with __import__("sqlite3").connect(db) as con:
                con.execute("INSERT INTO conversations(conversation_id,title,created_at,updated_at,source_file,source_sha256,raw_json,transcript,state) VALUES(?,?,?,?,?,?,?,?,?)", ("lakota-project-1", "KeyGlass plan", "2026-07-06", "", "/export/keyglass.json", "x", "{}", "[user] KeyGlass uses GnuPG", "done"))
                con.execute("INSERT INTO analyses VALUES(?,?,?,?,?,?,?,?,?,?)", ("lakota-project-1", "LAKOTA", .95, "[]", "summary", "[]", '[\"KeyGlass\"]', "{}", "index-model", "now"))
            record_project_facts(db, "lakota-project-1", "KeyGlass", [{"category":"architecture_decision", "statement":"KeyGlass uses the existing GnuPG keyring as its source of truth.", "evidence":"The project scope avoids a separate key database.", "temporal_status":"current", "confidence":"HIGH"}])
            render_project_documents(db, root, "KeyGlass")
            project = root / "memory" / "lakota" / "projects" / "KeyGlass"
            for name in ("PROJECT.md", "CURRENT_STATE.md", "DECISIONS.md", "HISTORY.md", "KNOWN_ISSUES.md", "SOLUTIONS.md", "LESSONS_LEARNED.md"):
                self.assertTrue((project / name).is_file(), name)
            decision = (project / "DECISIONS.md").read_text()
            self.assertIn("existing GnuPG keyring", decision)
            self.assertIn("conversation_id=lakota-project-1", decision)
            self.assertIn("/export/keyglass.json", decision)

    def test_deepen_only_processes_unextracted_lakota_conversations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); db = root / "memory.sqlite3"; init_database(db)
            with __import__("sqlite3").connect(db) as con:
                con.execute("INSERT INTO conversations(conversation_id,title,created_at,updated_at,source_file,source_sha256,raw_json,transcript,state) VALUES(?,?,?,?,?,?,?,?,?)", ("lakota-1", "Hermes", "2026-01-01", "", "/export/a.json", "x", "{}", "[user] Hermes gateway", "done"))
                con.execute("INSERT INTO analyses VALUES(?,?,?,?,?,?,?,?,?,?)", ("lakota-1", "LAKOTA", .9, "[]", "summary", "[]", '["Hermes"]', "{}", "index-model", "now"))
            from unittest.mock import patch
            result = {"facts":[{"project":"Hermes","category":"configuration","statement":"Uses localhost gateway.","evidence":"user says localhost","confidence":"HIGH"}]}
            with patch("chatgpt_memory.ollama_deep_extract", return_value=result) as extract:
                self.assertEqual(deepen(db, root, 10, "local-model", "127.0.0.1:11434"), 1)
                self.assertEqual(deepen(db, root, 10, "local-model", "127.0.0.1:11434"), 0)
                extract.assert_called_once()


if __name__ == "__main__":
    unittest.main()
