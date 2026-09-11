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
import deep_memory_finalize as finalize


class DeepMemoryFinalizeTests(unittest.TestCase):
    def make_db(self, tmp):
        db = Path(tmp) / "memory.sqlite3"
        finalize.ensure_finalize_schema(db)
        with deep_memory.connect(db) as con:
            for cid, created in (("c1", "2026-09-01T00:00:00+00:00"), ("c2", "2026-09-10T00:00:00+00:00")):
                con.execute(
                    """INSERT INTO conversations
                       (conversation_id,title,created_at,updated_at,source_file,source_sha256,raw_json,
                        transcript,priority,state,attempts)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (cid, cid, created, created, "test.json", "sha", "{}", "", 0, "pending", 0),
                )
            con.execute(
                "INSERT INTO projects(slug,name,updated_at) VALUES('agenticos','AgenticOS','now')"
            )
        return db

    def add_item(self, con, cid, statement, status="current", category="configuration", namespace="lakota"):
        fingerprint = finalize.stable_hash([cid, statement, category])
        con.execute(
            """INSERT INTO knowledge_items
               (fingerprint,project_slug,category,title,statement,evidence,status,confidence,
                source_conversation_id,source_date,created_at,namespace,origin)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                fingerprint, "agenticos", category, "", statement, "user evidence", status, "0.95",
                cid, "2026-09-01" if cid == "c1" else "2026-09-10", "now", namespace, "stage3",
            ),
        )
        item_id = con.execute("SELECT id FROM knowledge_items WHERE fingerprint=?", (fingerprint,)).fetchone()[0]
        con.execute(
            "INSERT INTO knowledge_item_projects(knowledge_item_id,project_slug,relevance,source) VALUES(?,?,1.0,'stage3')",
            (item_id, "agenticos"),
        )
        con.execute(
            """INSERT INTO knowledge_evidence
               (knowledge_item_id,conversation_id,passage_ref,evidence_ref,evidence_text,source_date)
               VALUES(?,?,?,?,?,?)""",
            (item_id, cid, "p0000", "u0001", "user evidence", "2026-09-01" if cid == "c1" else "2026-09-10"),
        )
        return int(item_id)

    def add_cluster_context(self, con):
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS semantic_cluster_runs(
              run_id TEXT PRIMARY KEY, created_at TEXT, scope_json TEXT, embedding_model TEXT,
              sample_count INTEGER, vector_dimensions INTEGER, pca_dimensions INTEGER,
              umap_dimensions INTEGER, eps REAL, min_samples INTEGER, cluster_count INTEGER, noise_count INTEGER
            );
            CREATE TABLE IF NOT EXISTS conversation_reductions(
              run_id TEXT, conversation_id TEXT, cluster_id INTEGER, pca_json TEXT, umap_json TEXT,
              vis_x REAL, vis_y REAL, PRIMARY KEY(run_id,conversation_id)
            );
            CREATE TABLE IF NOT EXISTS semantic_clusters(
              run_id TEXT, cluster_id INTEGER, size INTEGER, label TEXT, description TEXT,
              PRIMARY KEY(run_id,cluster_id)
            );
            """
        )
        con.execute(
            "INSERT INTO semantic_cluster_runs VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            ("sem-test", "2026-09-11", '{"identity": null, "conversation_type": null}', "test", 2, 3, 2, 2, .8, 4, 1, 0),
        )
        con.execute("INSERT INTO semantic_clusters VALUES('sem-test',0,2,'AgenticOS memory','')")
        con.execute("INSERT INTO conversation_reductions VALUES('sem-test','c1',0,'[]','[]',0,0)")
        con.execute("INSERT INTO conversation_reductions VALUES('sem-test','c2',0,'[]','[]',1,1)")

    def test_exact_duplicates_group_and_keep_cluster_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = self.make_db(tmp)
            with deep_memory.connect(db) as con:
                self.add_cluster_context(con)
                a = self.add_item(con, "c1", "AgenticOS uses SQLite as its canonical memory database.")
                b = self.add_item(con, "c2", "AgenticOS uses SQLite as its canonical memory database.")
            stats = finalize.build_groups(db)
            self.assertEqual(stats["groups"], 1)
            self.assertEqual(stats["members"], 2)
            with deep_memory.connect(db) as con:
                group = con.execute("SELECT * FROM knowledge_groups").fetchone()
                context = json.loads(group["cluster_context_json"])
                self.assertEqual(group["member_count"], 2)
                self.assertEqual(context[0]["label"], "AgenticOS memory")
                members = {row[0] for row in con.execute("SELECT item_id FROM knowledge_group_members")}
                self.assertEqual(members, {a, b})

    def test_two_distinct_current_values_create_conflict_and_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = self.make_db(tmp)
            with deep_memory.connect(db) as con:
                self.add_item(con, "c1", "SSH port is 22.")
                self.add_item(con, "c2", "SSH port is 2222.")
            stats = finalize.build_groups(db)
            self.assertEqual(stats["conflicts"], 1)
            with deep_memory.connect(db) as con:
                conflict = con.execute("SELECT * FROM knowledge_conflicts WHERE resolution_status='open'").fetchone()
                review = con.execute("SELECT * FROM knowledge_review_queue WHERE kind='state_conflict'").fetchone()
            self.assertEqual(conflict["state_key"], "ssh port")
            self.assertIsNotNone(review)

    def test_current_and_superseded_state_link_without_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = self.make_db(tmp)
            with deep_memory.connect(db) as con:
                old = self.add_item(con, "c1", "SSH port is 22.", status="superseded")
                current = self.add_item(con, "c2", "SSH port is 2222.", status="current")
            stats = finalize.build_groups(db)
            self.assertEqual(stats["conflicts"], 0)
            with deep_memory.connect(db) as con:
                relation = con.execute(
                    "SELECT relation FROM knowledge_relations WHERE source_item_id=? AND target_item_id=?",
                    (current, old),
                ).fetchone()
            self.assertEqual(relation[0], "supersedes")

    def test_suppress_override_keeps_atomic_item_but_excludes_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = self.make_db(tmp)
            with deep_memory.connect(db) as con:
                item_id = self.add_item(con, "c1", "SSH port is 22.")
            finalize.add_override(db, f"suppress_item:{item_id}", "suppress_item", {}, "user correction")
            finalize.build_groups(db)
            with deep_memory.connect(db) as con:
                atomic = con.execute("SELECT count(*) FROM knowledge_items WHERE id=?", (item_id,)).fetchone()[0]
                grouped = con.execute("SELECT count(*) FROM knowledge_group_members WHERE item_id=?", (item_id,)).fetchone()[0]
            self.assertEqual(atomic, 1)
            self.assertEqual(grouped, 0)

    def test_snapshot_and_markdown_are_rebuildable_views(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = self.make_db(tmp)
            output = Path(tmp) / "memory"
            with deep_memory.connect(db) as con:
                self.add_cluster_context(con)
                self.add_item(con, "c1", "AgenticOS database path is chatgpt-memory/data/memory.sqlite3.")
                self.add_item(con, "c2", "Use tmux for long-running AgenticOS memory jobs.", category="workflow")
            finalize.build_groups(db)
            snap = finalize.build_snapshots(db)
            rendered = finalize.render_all(db, output)
            self.assertEqual(snap["snapshots"], 1)
            self.assertEqual(rendered["projects"], 1)
            folder = output / "lakota" / "projects" / "agenticos"
            self.assertTrue((folder / "CURRENT_STATE.md").exists())
            self.assertTrue((folder / "WORKFLOWS.md").exists())
            text = (folder / "README.md").read_text()
            self.assertIn("AgenticOS memory", text)
            self.assertIn("SQLite", (folder / "CURRENT_STATE.md").read_text())


if __name__ == "__main__":
    unittest.main()
