#!/usr/bin/env python3
"""Build searchable project dossiers from the canonical ChatGPT memory database.

This is deterministic and does not call an LLM. It turns existing conversation
routing and extracted facts into a many-to-many project index. Future extraction
passes can write richer items into the same schema without changing the CLI.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Iterable


SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    slug TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    aliases_json TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS conversation_projects (
    conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id),
    project_slug TEXT NOT NULL REFERENCES projects(slug),
    relevance REAL NOT NULL DEFAULT 0.5,
    rationale TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'analysis',
    PRIMARY KEY(conversation_id, project_slug)
);
CREATE INDEX IF NOT EXISTS idx_conversation_projects_project
    ON conversation_projects(project_slug, relevance DESC);
CREATE TABLE IF NOT EXISTS knowledge_items (
    id INTEGER PRIMARY KEY,
    fingerprint TEXT UNIQUE NOT NULL,
    project_slug TEXT NOT NULL REFERENCES projects(slug),
    category TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    statement TEXT NOT NULL,
    evidence TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'unknown',
    confidence TEXT NOT NULL DEFAULT 'UNKNOWN',
    source_conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id),
    source_date TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_knowledge_project_category
    ON knowledge_items(project_slug, category, source_date DESC);
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_items_fts USING fts5(
    project_slug, category, title, statement, evidence,
    content='knowledge_items', content_rowid='id'
);
"""

CATEGORY_MAP = {
    "known_issue": "error",
    "failed_approach": "error",
    "bug": "error",
    "error": "error",
    "successful_command": "solution",
    "solution": "solution",
    "architecture_decision": "decision",
    "decision_reason": "decision",
    "lesson_learned": "lesson",
    "configuration": "configuration",
    "workflow": "workflow",
    "project_status": "status",
    "system_state": "status",
    "important_fact": "fact",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:80] or "uncategorized"


def markdown(value: str) -> str:
    return value.replace("\r", " ").strip()


def connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA)


def project_names(connection: sqlite3.Connection) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in connection.execute("SELECT projects_json FROM analyses"):
        try:
            values = json.loads(row[0])
        except (TypeError, json.JSONDecodeError):
            continue
        for value in values if isinstance(values, list) else []:
            name = str(value).strip()
            if name:
                result.setdefault(slugify(name), name)
    for table in ("project_facts", "deep_facts"):
        if not has_table(connection, table):
            continue
        for row in connection.execute(f"SELECT DISTINCT project FROM {table}"):
            name = str(row[0]).strip()
            if name:
                result.setdefault(slugify(name), name)
    return result


def has_table(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def populate_projects(connection: sqlite3.Connection) -> None:
    timestamp = now()
    names = project_names(connection)
    for slug, name in names.items():
        connection.execute(
            """INSERT INTO projects(slug,name,updated_at) VALUES(?,?,?)
               ON CONFLICT(slug) DO UPDATE SET name=excluded.name,updated_at=excluded.updated_at""",
            (slug, name, timestamp),
        )

    for row in connection.execute("SELECT conversation_id,identity,confidence,projects_json,reasons_json FROM analyses"):
        try:
            projects = json.loads(row["projects_json"])
            reasons = json.loads(row["reasons_json"])
        except (TypeError, json.JSONDecodeError):
            continue
        relevance = max(0.05, min(1.0, float(row["confidence"])))
        rationale = "; ".join(str(reason) for reason in reasons[:3]) if isinstance(reasons, list) else ""
        for name in projects if isinstance(projects, list) else []:
            slug = slugify(str(name))
            if slug not in names:
                continue
            connection.execute(
                """INSERT INTO conversation_projects
                   (conversation_id,project_slug,relevance,rationale,source) VALUES(?,?,?,?,?)
                   ON CONFLICT(conversation_id,project_slug) DO UPDATE SET
                     relevance=excluded.relevance,rationale=excluded.rationale,source=excluded.source""",
                (row["conversation_id"], slug, relevance, rationale, f"analysis:{row['identity'].lower()}"),
            )


def normalized_items(connection: sqlite3.Connection) -> Iterable[dict[str, str]]:
    seen: set[tuple[str, str, str, str]] = set()
    for table in ("project_facts", "deep_facts"):
        if not has_table(connection, table):
            continue
        columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
        status_column = "temporal_status" if "temporal_status" in columns else "'unknown'"
        query = f"""SELECT project,category,statement,evidence,{status_column} AS status,
                           confidence,source_conversation_id,source_date
                    FROM {table}"""
        for row in connection.execute(query):
            category = CATEGORY_MAP.get(row["category"], row["category"] or "fact")
            key = (row["source_conversation_id"], row["project"], category, row["statement"])
            if key in seen:
                continue
            seen.add(key)
            yield {
                "project_slug": slugify(row["project"]),
                "category": category,
                "title": "",
                "statement": row["statement"],
                "evidence": row["evidence"],
                "status": row["status"] or "unknown",
                "confidence": row["confidence"] or "UNKNOWN",
                "source_conversation_id": row["source_conversation_id"],
                "source_date": row["source_date"] or "",
            }


def populate_knowledge(connection: sqlite3.Connection) -> int:
    count = 0
    for item in normalized_items(connection):
        raw = "\x1f".join(
            [item["source_conversation_id"], item["project_slug"], item["category"], item["statement"]]
        )
        fingerprint = hashlib.sha256(raw.encode()).hexdigest()
        connection.execute(
            """INSERT INTO knowledge_items
               (fingerprint,project_slug,category,title,statement,evidence,status,confidence,
                source_conversation_id,source_date,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(fingerprint) DO UPDATE SET evidence=excluded.evidence,status=excluded.status,
                 confidence=excluded.confidence,source_date=excluded.source_date""",
            (
                fingerprint,
                item["project_slug"],
                item["category"],
                item["title"],
                item["statement"],
                item["evidence"],
                item["status"],
                item["confidence"],
                item["source_conversation_id"],
                item["source_date"],
                now(),
            ),
        )
        count += 1
    connection.execute("INSERT INTO knowledge_items_fts(knowledge_items_fts) VALUES('rebuild')")
    return count


def render_project(connection: sqlite3.Connection, output: Path, project: sqlite3.Row) -> None:
    folder = output / "projects" / project["slug"]
    folder.mkdir(parents=True, exist_ok=True)
    conversations = connection.execute(
        """SELECT c.conversation_id,c.title,c.created_at,cp.relevance,cp.rationale
           FROM conversation_projects cp JOIN conversations c USING(conversation_id)
           WHERE cp.project_slug=? ORDER BY c.created_at""",
        (project["slug"],),
    ).fetchall()
    items = connection.execute(
        """SELECT * FROM knowledge_items WHERE project_slug=?
           ORDER BY source_date,category,id""",
        (project["slug"],),
    ).fetchall()
    by_category: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for item in items:
        by_category[item["category"]].append(item)

    overview = [
        f"# {project['name']}",
        "",
        "Source-backed knowledge assembled from conversations that may belong to multiple projects.",
        "",
        f"- Conversations: {len(conversations)}",
        f"- Knowledge items: {len(items)}",
        f"- Errors/issues: {len(by_category['error'])}",
        "",
        "## Knowledge sections",
        "",
    ]
    for category in sorted(by_category):
        overview.append(f"- [{category.title()}]({category.upper()}.md): {len(by_category[category])}")
    (folder / "README.md").write_text("\n".join(overview) + "\n", encoding="utf-8")

    for category, rows in by_category.items():
        lines = [f"# {project['name']} — {category.title()}", ""]
        for row in rows:
            lines.extend(
                [
                    f"## {markdown(row['statement'])}",
                    "",
                    markdown(row["evidence"]),
                    "",
                    f"- Status: `{row['status']}`",
                    f"- Confidence: `{row['confidence']}`",
                    f"- Source conversation: `{row['source_conversation_id']}`",
                    f"- Source date: `{row['source_date']}`",
                    "",
                ]
            )
        (folder / f"{category.upper()}.md").write_text("\n".join(lines), encoding="utf-8")

    sources = [f"# {project['name']} — Source Conversations", ""]
    for row in conversations:
        sources.extend(
            [
                f"- **{markdown(row['title'])}** — `{row['conversation_id']}`",
                f"  - Date: `{row['created_at']}`; relevance: `{row['relevance']:.2f}`",
                f"  - Routing evidence: {markdown(row['rationale']) or 'not recorded'}",
            ]
        )
    (folder / "SOURCES.md").write_text("\n".join(sources) + "\n", encoding="utf-8")


def render_all(connection: sqlite3.Connection, output: Path) -> int:
    output.mkdir(parents=True, exist_ok=True)
    projects = connection.execute("SELECT * FROM projects ORDER BY name COLLATE NOCASE").fetchall()
    index = ["# ChatGPT Project Knowledge", "", "Each conversation may appear under multiple projects.", ""]
    for project in projects:
        render_project(connection, output, project)
        counts = connection.execute(
            """SELECT COUNT(DISTINCT cp.conversation_id),COUNT(DISTINCT ki.id)
               FROM projects p LEFT JOIN conversation_projects cp ON cp.project_slug=p.slug
               LEFT JOIN knowledge_items ki ON ki.project_slug=p.slug WHERE p.slug=?""",
            (project["slug"],),
        ).fetchone()
        index.append(
            f"- [{project['name']}](projects/{project['slug']}/README.md) — "
            f"{counts[0]} conversations, {counts[1]} knowledge items"
        )
    (output / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    return len(projects)


def build(database: Path, output: Path) -> dict[str, int]:
    with connect(database) as connection:
        ensure_schema(connection)
        populate_projects(connection)
        items = populate_knowledge(connection)
        projects = render_all(connection, output)
        conversations = connection.execute("SELECT COUNT(*) FROM conversation_projects").fetchone()[0]
        connection.commit()
    return {"projects": projects, "conversation_project_links": conversations, "knowledge_items": items}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build searchable ChatGPT project knowledge")
    parser.add_argument("command", choices=["build"])
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.db.expanduser(), args.output.expanduser()), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
