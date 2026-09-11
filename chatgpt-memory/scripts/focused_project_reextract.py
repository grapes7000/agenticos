#!/usr/bin/env python3
"""Targeted, source-grounded retry for empty project dossiers and failed chunks."""
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from chatgpt_memory import (  # noqa: E402
    connect,
    now,
    ollama_project_extract,
    project_chunks,
    record_project_facts,
    render_project_documents,
)

DB = ROOT / "data" / "memory.sqlite3"
MODEL = "qwen3:32b"
HOST = "192.168.122.1:11434"

# Force the target project as the only allowed recipient. This prevents facts from a
# multi-project transcript being routed to a better-known competing project.
EMPTY_PROJECT_SOURCES = {
    "Byterover-integration": "6a519eaa-be18-83e8-9a08-b4b65fee80ed",
    "Soul-md-creation": "6a519eaa-be18-83e8-9a08-b4b65fee80ed",
    "Troubleshooting-display-issues-in-QTile": "6a51be18-1bc0-83e8-9391-1075bc8e0ebe",
}

# These were the only chunks whose original extractor output was malformed JSON.
FAILED_CHUNKS = {
    "6a3b12da-7664-83e8-8047-18ef8c3951be": {
        "chunks": [13, 14],
        "projects": ["Hermes", "Homelab-Self-Hosting", "Local-AI-Infrastructure", "Virtualization"],
    }
}


def conversation(cid: str):
    with connect(DB) as con:
        return con.execute(
            "SELECT conversation_id,title,transcript FROM conversations WHERE conversation_id=?", (cid,)
        ).fetchone()


def process_target_project(project: str, cid: str) -> tuple[int, int]:
    row = conversation(cid)
    saved = 0
    errors = 0
    for idx, chunk in enumerate(project_chunks(row["transcript"])):
        try:
            facts = ollama_project_extract(row["title"], [project], chunk, MODEL, HOST)
            saved += record_project_facts(DB, cid, project, facts)
            print(f"target project={project} chunk={idx} facts={len(facts)} saved={saved}", flush=True)
        except Exception as exc:
            errors += 1
            with connect(DB) as con:
                con.execute(
                    "INSERT INTO events(at,kind,detail) VALUES(?,?,?)",
                    (now(), "focused-project-reextract-error", f"{cid}/{idx}/{project}: {type(exc).__name__}: {exc}"[:2000]),
                )
            print(f"ERROR target project={project} chunk={idx}: {type(exc).__name__}: {exc}", flush=True)
    return saved, errors


def process_failed_chunk(cid: str, idx: int, projects: list[str]) -> tuple[int, int]:
    row = conversation(cid)
    chunk = project_chunks(row["transcript"])[idx]
    try:
        facts = ollama_project_extract(row["title"], projects, chunk, MODEL, HOST)
        saved = sum(record_project_facts(DB, cid, project, [fact for fact in facts if fact["project"] == project]) for project in projects)
        with connect(DB) as con:
            con.execute(
                "INSERT OR IGNORE INTO project_extraction_chunks VALUES(?,?,?,?,?)",
                (cid, "__ALL_PROJECTS__", idx, MODEL, now()),
            )
        print(f"retry chunk={idx} facts={len(facts)} saved={saved}", flush=True)
        return saved, 0
    except Exception as exc:
        with connect(DB) as con:
            con.execute(
                "INSERT INTO events(at,kind,detail) VALUES(?,?,?)",
                (now(), "focused-project-reextract-error", f"{cid}/{idx}: {type(exc).__name__}: {exc}"[:2000]),
            )
        print(f"ERROR retry chunk={idx}: {type(exc).__name__}: {exc}", flush=True)
        return 0, 1


def main() -> int:
    backup = DB.with_suffix(".sqlite3.before-focused-pass.bak")
    if not backup.exists():
        shutil.copy2(DB, backup)
        print(f"backup={backup}", flush=True)
    else:
        print(f"backup exists={backup}", flush=True)

    saved = errors = 0
    for project, cid in EMPTY_PROJECT_SOURCES.items():
        count, failed = process_target_project(project, cid)
        saved += count
        errors += failed

    for cid, spec in FAILED_CHUNKS.items():
        for idx in spec["chunks"]:
            count, failed = process_failed_chunk(cid, idx, spec["projects"])
            saved += count
            errors += failed

    for project in set(EMPTY_PROJECT_SOURCES) | {p for spec in FAILED_CHUNKS.values() for p in spec["projects"]}:
        render_project_documents(DB, ROOT, project)

    with sqlite3.connect(DB) as con:
        total = con.execute("SELECT COUNT(*) FROM project_facts").fetchone()[0]
        coverage = con.execute("SELECT COUNT(DISTINCT project) FROM project_facts").fetchone()[0]
    print(f"RESULT saved={saved} errors={errors} total_facts={total} fact_projects={coverage}", flush=True)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
