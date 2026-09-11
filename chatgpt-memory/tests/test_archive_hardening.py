import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from chatgpt_archive import (  # noqa: E402
    index_asset_embeddings,
    index_assets,
    index_conversation_embeddings,
    ingest_conversations,
    link_asset_references,
)


def conversation(text="hello", asset_ids=(), duplicate_pointer=False):
    attachments = [
        {
            "asset_pointer": f"file-service://file-{asset_id}",
            "name": f"{asset_id}.png",
            "mime_type": "image/png",
        }
        for asset_id in asset_ids
    ]
    parts = [text]
    if duplicate_pointer and asset_ids:
        parts.append(f"file-service://file-{asset_ids[0]}")
    return {
        "id": "conv-1",
        "title": "Hardening test",
        "create_time": 1,
        "update_time": 2,
        "current_node": "u1",
        "mapping": {
            "u1": {
                "parent": None,
                "message": {
                    "id": "m1",
                    "create_time": 1,
                    "author": {"role": "user"},
                    "content": {"parts": parts},
                    "metadata": {"attachments": attachments},
                },
            }
        },
    }


class ArchiveHardeningTests(unittest.TestCase):
    def test_no_embeddings_preserves_existing_chat_vector_across_model_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "export"
            source.mkdir()
            db = root / "memory.sqlite3"
            (source / "conversations-000.json").write_text(json.dumps([conversation()]))
            ingest_conversations(db, source)

            with patch("chatgpt_archive.embed", return_value=[1.0, 0.0]):
                index_conversation_embeddings(db, model="model-a")

            with sqlite3.connect(db) as con:
                before = con.execute(
                    "SELECT embedding_json,embedding_model FROM chat_chunks"
                ).fetchone()

            index_conversation_embeddings(db, model="model-b", do_embed=False)

            with sqlite3.connect(db) as con:
                after = con.execute(
                    "SELECT embedding_json,embedding_model FROM chat_chunks"
                ).fetchone()
            self.assertEqual(after, before)

    def test_no_embeddings_preserves_existing_asset_vector_across_model_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "export"
            source.mkdir()
            db = root / "memory.sqlite3"
            aid = "0123456789abcdef0123456789abcdef"
            (source / "conversations-000.json").write_text(
                json.dumps([conversation("image context", [aid])])
            )
            (source / f"file_{aid}.dat").write_bytes(b"\x89PNG\r\n\x1a\n" + b"same-image")
            ingest_conversations(db, source)
            index_assets(db, source)
            link_asset_references(db)

            with patch("chatgpt_archive.embed", return_value=[0.5, 0.5]):
                index_asset_embeddings(db, model="model-a")

            with sqlite3.connect(db) as con:
                before = con.execute(
                    "SELECT embedding_json,embedding_model FROM asset_chunks WHERE embedding_json IS NOT NULL"
                ).fetchone()
            self.assertIsNotNone(before)

            index_asset_embeddings(db, model="model-b", do_embed=False)

            with sqlite3.connect(db) as con:
                after = con.execute(
                    "SELECT embedding_json,embedding_model FROM asset_chunks WHERE embedding_json IS NOT NULL"
                ).fetchone()
            self.assertEqual(after, before)

    def test_duplicate_binary_assets_are_deduplicated_by_sha_with_aliases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "export"
            source.mkdir()
            db = root / "memory.sqlite3"
            aid1 = "11111111111111111111111111111111"
            aid2 = "22222222222222222222222222222222"
            payload = b"\x89PNG\r\n\x1a\n" + b"identical"
            (source / f"file_{aid1}.dat").write_bytes(payload)
            (source / f"file_{aid2}.dat").write_bytes(payload)

            result = index_assets(db, source)
            self.assertEqual(result["files"], 2)
            self.assertEqual(result["assets"], 1)
            self.assertEqual(result["deduplicated"], 1)

            with sqlite3.connect(db) as con:
                self.assertEqual(con.execute("SELECT count(*) FROM assets").fetchone()[0], 1)
                aliases = con.execute(
                    "SELECT alias_id,asset_id FROM asset_aliases ORDER BY alias_id"
                ).fetchall()
            self.assertEqual(len(aliases), 2)
            self.assertEqual(aliases[0][1], aliases[1][1])

    def test_extension_correct_asset_is_discovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "export"
            source.mkdir()
            db = root / "memory.sqlite3"
            (source / "photo.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"payload")

            result = index_assets(db, source)
            self.assertEqual(result["files"], 1)
            self.assertEqual(result["assets"], 1)
            with sqlite3.connect(db) as con:
                mime = con.execute("SELECT detected_mime FROM assets").fetchone()[0]
            self.assertEqual(mime, "image/png")

    def test_duplicate_attachment_representations_link_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "export"
            source.mkdir()
            db = root / "memory.sqlite3"
            aid = "0123456789abcdef0123456789abcdef"
            (source / "conversations-000.json").write_text(
                json.dumps([conversation("look at this", [aid], duplicate_pointer=True)])
            )
            (source / f"file_{aid}.dat").write_bytes(b"\x89PNG\r\n\x1a\n" + b"payload")

            ingest_conversations(db, source)
            index_assets(db, source)
            result = link_asset_references(db)

            self.assertEqual(result["linked_assets"], 1)
            self.assertEqual(result["references"], 1)
            with sqlite3.connect(db) as con:
                self.assertEqual(con.execute("SELECT count(*) FROM asset_references").fetchone()[0], 1)

    def test_chat_chunk_hash_can_move_to_another_index_without_unique_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "export"
            source.mkdir()
            db = root / "memory.sqlite3"
            (source / "conversations-000.json").write_text(json.dumps([conversation("hello")]))
            ingest_conversations(db, source)

            with patch("chatgpt_archive.embed", return_value=[1.0, 0.0]):
                index_conversation_embeddings(db, model="model-a")

            with sqlite3.connect(db) as con:
                before = con.execute(
                    "SELECT chunk_hash,embedding_json,embedding_model FROM chat_chunks WHERE chunk_index=0"
                ).fetchone()
                con.execute("UPDATE chat_chunks SET chunk_index=99 WHERE chunk_index=0")

            result = index_conversation_embeddings(db, model="model-b", do_embed=False)
            self.assertGreater(result["reused"], 0)

            with sqlite3.connect(db) as con:
                after = con.execute(
                    "SELECT chunk_hash,embedding_json,embedding_model FROM chat_chunks WHERE chunk_index=0"
                ).fetchone()
                stale = con.execute("SELECT count(*) FROM chat_chunks WHERE chunk_index=99").fetchone()[0]
            self.assertEqual(after, before)
            self.assertEqual(stale, 0)

    def test_asset_chunk_hash_can_move_to_another_index_without_unique_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "export"
            source.mkdir()
            db = root / "memory.sqlite3"
            aid = "0123456789abcdef0123456789abcdef"
            (source / "conversations-000.json").write_text(
                json.dumps([conversation("image context", [aid])])
            )
            (source / f"file_{aid}.dat").write_bytes(b"\x89PNG\r\n\x1a\n" + b"payload")
            ingest_conversations(db, source)
            index_assets(db, source)
            link_asset_references(db)

            with patch("chatgpt_archive.embed", return_value=[0.5, 0.5]):
                index_asset_embeddings(db, model="model-a")

            with sqlite3.connect(db) as con:
                before = con.execute(
                    "SELECT chunk_hash,embedding_json,embedding_model FROM asset_chunks WHERE chunk_index=0"
                ).fetchone()
                con.execute("UPDATE asset_chunks SET chunk_index=99 WHERE chunk_index=0")

            result = index_asset_embeddings(db, model="model-b", do_embed=False)
            self.assertGreater(result["reused"], 0)

            with sqlite3.connect(db) as con:
                after = con.execute(
                    "SELECT chunk_hash,embedding_json,embedding_model FROM asset_chunks WHERE chunk_index=0"
                ).fetchone()
                stale = con.execute("SELECT count(*) FROM asset_chunks WHERE chunk_index=99").fetchone()[0]
            self.assertEqual(after, before)
            self.assertEqual(stale, 0)


if __name__ == "__main__":
    unittest.main()