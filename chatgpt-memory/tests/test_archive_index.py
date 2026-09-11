import json
import sqlite3
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from chatgpt_archive import (  # noqa: E402
    detect_mime,
    extract_asset_text,
    index_asset_embeddings,
    index_assets,
    index_conversation_embeddings,
    ingest_conversations,
    link_asset_references,
    materialize_assets,
)


def conversation(text: str = "hello", asset_id: str | None = None) -> dict:
    metadata = {}
    if asset_id:
        metadata = {
            "attachments": [
                {
                    "asset_pointer": f"file-service://file-{asset_id}",
                    "name": "picture.png",
                    "mime_type": "image/png",
                }
            ]
        }
    return {
        "id": "conv-1",
        "title": "Test conversation",
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
                    "content": {"parts": [text]},
                    "metadata": metadata,
                },
            }
        },
    }


class ArchiveIndexTests(unittest.TestCase):
    def test_reimport_skips_unchanged_and_reindexes_changed_conversation_vectors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "export"
            source.mkdir()
            db = root / "memory.sqlite3"
            export_file = source / "conversations-000.json"
            export_file.write_text(json.dumps([conversation("hello")]))

            first = ingest_conversations(db, source)
            self.assertEqual(first["added"], 1)
            second = ingest_conversations(db, source)
            self.assertEqual(second["unchanged"], 1)

            with patch("chatgpt_archive.embed", return_value=[1.0, 0.0]):
                indexed = index_conversation_embeddings(db)
                self.assertGreater(indexed["embedded"], 0)
                indexed_again = index_conversation_embeddings(db)
                self.assertGreater(indexed_again["reused"], 0)

            export_file.write_text(json.dumps([conversation("changed text")]))
            changed = ingest_conversations(db, source)
            self.assertEqual(changed["updated"], 1)
            with sqlite3.connect(db) as con:
                self.assertEqual(con.execute("SELECT count(*) FROM chat_chunks").fetchone()[0], 1)
                transcript = con.execute("SELECT transcript FROM conversations").fetchone()[0]
            self.assertIn("changed text", transcript)

            with patch("chatgpt_archive.embed", return_value=[0.0, 1.0]):
                reindexed = index_conversation_embeddings(db)
                self.assertGreater(reindexed["embedded"], 0)

            with sqlite3.connect(db) as con:
                chunk_text = con.execute(
                    "SELECT chunk_text FROM chat_chunks WHERE chunk_index=0"
                ).fetchone()[0]
            self.assertIn("changed text", chunk_text)

    def test_metadata_only_change_preserves_existing_deep_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "export"
            source.mkdir()
            db = root / "memory.sqlite3"
            export_file = source / "conversations-000.json"

            original = conversation("hello")
            export_file.write_text(json.dumps([original]))
            ingest_conversations(db, source)

            with sqlite3.connect(db) as con:
                con.execute("""
                    INSERT INTO deep_facts
                    (source_conversation_id, project, category, statement, evidence,
                     confidence, identity, source_file, source_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "conv-1", "AgenticOS", "decision", "Keep this memory",
                    "existing analysis", "high", "LAKOTA", "old-export.json",
                    "2026-09-01"
                ))

            metadata_changed = conversation("hello")
            metadata_changed["is_starred"] = True
            export_file.write_text(json.dumps([metadata_changed]))

            result = ingest_conversations(db, source)

            self.assertEqual(result["unchanged"], 1)
            self.assertEqual(result["updated"], 0)
            with sqlite3.connect(db) as con:
                count = con.execute(
                    "SELECT count(*) FROM deep_facts WHERE source_conversation_id='conv-1'"
                ).fetchone()[0]
            self.assertEqual(count, 1)

    def test_changed_conversation_preserves_unchanged_chunk_embeddings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "export"
            source.mkdir()
            db = root / "memory.sqlite3"
            export_file = source / "conversations-000.json"

            conv = conversation("A" * 2700)
            export_file.write_text(json.dumps([conv]))
            ingest_conversations(db, source)

            with patch("chatgpt_archive.embed", return_value=[1.0, 0.0]):
                index_conversation_embeddings(db)

            with sqlite3.connect(db) as con:
                first_hash, first_embedding = con.execute(
                    "SELECT chunk_hash, embedding_json FROM chat_chunks WHERE chunk_index=0"
                ).fetchone()

            conv["mapping"]["a2"] = {
                "parent": "u1",
                "message": {
                    "id": "m2",
                    "create_time": 2,
                    "author": {"role": "assistant"},
                    "content": {"parts": ["new reply"]},
                    "metadata": {},
                },
            }
            conv["current_node"] = "a2"
            export_file.write_text(json.dumps([conv]))

            changed = ingest_conversations(db, source)
            self.assertEqual(changed["updated"], 1)

            with sqlite3.connect(db) as con:
                row = con.execute(
                    "SELECT chunk_hash, embedding_json FROM chat_chunks WHERE chunk_index=0"
                ).fetchone()

            self.assertIsNotNone(row)
            self.assertEqual(row[0], first_hash)
            self.assertEqual(row[1], first_embedding)

    def test_dat_image_is_recovered_linked_and_search_context_is_embedded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "export"
            source.mkdir()
            db = root / "memory.sqlite3"
            asset_id = "0123456789abcdef0123456789abcdef"
            (source / "conversations-000.json").write_text(
                json.dumps([conversation("this is the pink desktop screenshot", asset_id)])
            )
            (source / f"file_{asset_id}.dat").write_bytes(b"\x89PNG\r\n\x1a\n" + b"payload")

            ingest_conversations(db, source)
            assets = index_assets(db, source)
            self.assertEqual(assets["assets"], 1)
            references = link_asset_references(db)
            self.assertEqual(references["linked_assets"], 1)
            materialize_assets(db, root / "asset-view")

            with sqlite3.connect(db) as con:
                mime, recovered = con.execute(
                    "SELECT detected_mime,recovered_path FROM assets"
                ).fetchone()
            self.assertEqual(mime, "image/png")
            self.assertTrue(recovered.endswith(".png"))

            with patch("chatgpt_archive.embed", return_value=[0.5, 0.5]):
                embedded = index_asset_embeddings(db)
                self.assertGreater(embedded["embedded"], 0)
            with sqlite3.connect(db) as con:
                chunk_text, kind = con.execute(
                    "SELECT chunk_text,content_kind FROM asset_chunks"
                ).fetchone()
            self.assertIn("pink desktop", chunk_text)
            self.assertEqual(kind, "conversation_context")

    def test_docx_dat_extracts_document_text_without_renaming_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "file_0123456789abcdef.dat"
            document_xml = (
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                '<w:body><w:p><w:r><w:t>Hello document</w:t></w:r></w:p></w:body></w:document>'
            )
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", document_xml)
            mime = detect_mime(path)
            self.assertIn("wordprocessingml.document", mime)
            text, status = extract_asset_text(path, mime)
            self.assertEqual(status, "extracted")
            self.assertIn("Hello document", text)
            self.assertTrue(path.exists())
            self.assertEqual(path.suffix, ".dat")


if __name__ == "__main__":
    unittest.main()
