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


def raw_conversation(messages):
    mapping = {}
    parent = None
    for index, (role, text) in enumerate(messages, 1):
        node_id = f"n{index}"
        mapping[node_id] = {
            "parent": parent,
            "message": {
                "author": {"role": role},
                "content": {"parts": [text]},
                "create_time": index,
            },
        }
        parent = node_id
    return {"id": "c1", "current_node": parent, "mapping": mapping}


class DeepMemoryStage3Tests(unittest.TestCase):
    def make_db(self, tmp, messages=None, projects=None):
        db = Path(tmp) / "memory.sqlite3"
        deep_memory.ensure_schema(db)
        raw = raw_conversation(messages or [("user", "AgenticOS uses SQLite for its local memory database.")])
        with deep_memory.connect(db) as con:
            con.execute(
                """INSERT INTO conversations
                   (conversation_id,title,created_at,updated_at,source_file,source_sha256,raw_json,
                    transcript,priority,state,attempts)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    "c1", "AgenticOS memory", "2026-09-10T12:00:00+00:00", "", "test.json",
                    "sha", json.dumps(raw), "transcript", 0, "pending", 0,
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
                    "c1", "LAKOTA", "AgenticOS memory work", "[]",
                    json.dumps(projects or ["AgenticOS"]), "development", 5, "test", "now",
                ),
            )
        return db

    def test_queue_is_idempotent_and_invalidates_changed_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = self.make_db(tmp)
            first = deep_memory.queue_conversations(db, "test-model")
            self.assertGreater(first["queued"], 0)
            with deep_memory.connect(db) as con:
                con.execute("UPDATE deep_memory_extractions SET state='done'")

            second = deep_memory.queue_conversations(db, "test-model")
            self.assertEqual(second["queued"], 0)
            self.assertGreater(second["reused"], 0)

            changed = raw_conversation([
                ("user", "AgenticOS uses SQLite for its local memory database."),
                ("user", "The deep-memory design changed and now needs source-backed evidence."),
            ])
            with deep_memory.connect(db) as con:
                con.execute(
                    "UPDATE conversations SET raw_json=? WHERE conversation_id='c1'",
                    (json.dumps(changed),),
                )

            third = deep_memory.queue_conversations(db, "test-model")
            self.assertGreater(third["invalidated"], 0)
            with deep_memory.connect(db) as con:
                states = [row[0] for row in con.execute(
                    "SELECT state FROM deep_memory_extractions WHERE conversation_id='c1'"
                )]
            self.assertTrue(states)
            self.assertTrue(all(state == "queued" for state in states))

    def test_passages_preserve_message_refs_and_overlap(self):
        conv = raw_conversation([
            ("user", "A" * 900),
            ("assistant", "B" * 900),
            ("user", "C" * 900),
            ("assistant", "D" * 900),
        ])
        passages = deep_memory.build_passages(conv, target_chars=2100)
        self.assertGreaterEqual(len(passages), 2)
        self.assertTrue(all(p["refs"] for p in passages))
        self.assertEqual(passages[0]["turns"][-1]["ref"], passages[1]["turns"][0]["ref"])
        self.assertTrue(any(ref.startswith("u") for ref in passages[0]["refs"]))

    def test_solution_requires_user_success_confirmation(self):
        passage = {
            "turns": [
                {"ref": "u0001", "role": "user", "text": "SSH is failing."},
                {"ref": "a0002", "role": "assistant", "text": "Restart sshd."},
                {"ref": "u0003", "role": "user", "text": "That worked; SSH connects now."},
            ]
        }
        valid = deep_memory.normalize_item(
            {
                "category": "confirmed_solution",
                "statement": "Restarting sshd restored SSH connectivity.",
                "projects": ["Homelab-Self-Hosting"],
                "confidence": 0.95,
                "temporal_status": "current",
                "evidence": "The user reported SSH was failing.",
                "evidence_ref": "u0001",
                "success_evidence": "The user explicitly said the restart worked.",
                "success_evidence_ref": "u0003",
                "related_item_hint": "same SSH failure",
            },
            passage,
        )
        self.assertEqual(valid["promotion_state"], "pending")

        assistant_only = deep_memory.normalize_item(
            {
                "category": "configuration",
                "statement": "SSH should run on port 2222.",
                "projects": [],
                "confidence": 0.8,
                "temporal_status": "unknown",
                "evidence": "The assistant suggested port 2222.",
                "evidence_ref": "a0002",
                "success_evidence": "",
                "success_evidence_ref": "",
                "related_item_hint": "",
            },
            passage,
        )
        self.assertEqual(assistant_only["promotion_state"], "blocked_assistant_only")

        unconfirmed = deep_memory.normalize_item(
            {
                "category": "confirmed_solution",
                "statement": "Restarting sshd fixed SSH.",
                "projects": [],
                "confidence": 0.8,
                "temporal_status": "unknown",
                "evidence": "The user reported SSH was failing.",
                "evidence_ref": "u0001",
                "success_evidence": "The assistant predicted it would work.",
                "success_evidence_ref": "a0002",
                "related_item_hint": "",
            },
            passage,
        )
        self.assertEqual(unconfirmed["promotion_state"], "blocked_unconfirmed_solution")

    def seed_candidates(self, db):
        queued = deep_memory.queue_conversations(db, "test-model")
        self.assertGreater(queued["queued"], 0)
        with deep_memory.connect(db) as con:
            extraction = con.execute(
                "SELECT * FROM deep_memory_extractions WHERE conversation_id='c1' ORDER BY passage_index LIMIT 1"
            ).fetchone()
            con.execute("UPDATE deep_memory_extractions SET state='done' WHERE extraction_id=?", (extraction["extraction_id"],))
            rows = [
                (
                    "error", "Ollama returned HTTP 500 while embedding a large chunk.", ["AgenticOS"],
                    "The user pasted the HTTP 500 failure.", "u0001", "", "", "embedding failure",
                ),
                (
                    "failed_approach", "Retrying the legacy embeddings endpoint did not solve the failure.", ["AgenticOS"],
                    "The user reported the same failure after the retry.", "u0001", "", "", "embedding failure",
                ),
                (
                    "confirmed_solution", "Using /api/embed with truncate=true resolved embedding failures.", ["Local-AI-Infrastructure"],
                    "The user tested the modern endpoint.", "u0001", "The user confirmed the import completed successfully.", "u0001", "embedding failure",
                ),
            ]
            for index, row in enumerate(rows):
                category, statement, projects, evidence, evidence_ref, success, success_ref, hint = row
                con.execute(
                    """INSERT INTO deep_memory_candidates
                       (extraction_id,item_index,namespace,category,statement,projects_json,confidence,
                        temporal_status,evidence,evidence_ref,success_evidence,success_evidence_ref,
                        related_item_hint,source_date,promotion_state,raw_json)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        extraction["extraction_id"], index, "lakota", category, statement,
                        json.dumps(projects), 0.95, "current", evidence, evidence_ref, success,
                        success_ref, hint, "2026-09-10T12:00:00+00:00", "pending", "{}",
                    ),
                )

    def test_writer_preserves_namespace_provenance_and_many_to_many_projects(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = self.make_db(tmp, projects=["AgenticOS"])
            self.seed_candidates(db)
            result = deep_memory.write_knowledge(db)
            self.assertEqual(result["promoted"], 3)
            with deep_memory.connect(db) as con:
                solution = con.execute(
                    "SELECT id,namespace,origin FROM knowledge_items WHERE category='confirmed_solution'"
                ).fetchone()
                self.assertEqual(solution["namespace"], "lakota")
                self.assertEqual(solution["origin"], "stage3")
                projects = {
                    row[0] for row in con.execute(
                        "SELECT project_slug FROM knowledge_item_projects WHERE knowledge_item_id=?",
                        (solution["id"],),
                    )
                }
                self.assertIn("agenticos", projects)
                self.assertIn("local-ai-infrastructure", projects)
                evidence = con.execute(
                    "SELECT count(*) FROM knowledge_evidence WHERE knowledge_item_id=?",
                    (solution["id"],),
                ).fetchone()[0]
                self.assertEqual(evidence, 1)

    def test_error_attempt_solution_chain_is_linked(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = self.make_db(tmp, projects=["AgenticOS"])
            self.seed_candidates(db)
            deep_memory.write_knowledge(db)
            stats = deep_memory.link_relations(db)
            self.assertEqual(stats["error_attempt"], 1)
            self.assertEqual(stats["error_solution"], 1)
            with deep_memory.connect(db) as con:
                relations = {
                    row[0] for row in con.execute(
                        "SELECT relation FROM knowledge_relations WHERE source='stage3'"
                    )
                }
            self.assertEqual(relations, {"failed_approach", "confirmed_solution"})


if __name__ == "__main__":
    unittest.main()
