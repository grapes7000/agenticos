from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from .settings import Settings


def _connect(settings: Settings) -> sqlite3.Connection:
    if not settings.memory_database.is_file():
        raise FileNotFoundError(f"ChatGPT memory database not found: {settings.memory_database}")
    connection = sqlite3.connect(settings.memory_database)
    connection.row_factory = sqlite3.Row
    return connection


def list_projects(settings: Settings) -> list[dict[str, object]]:
    with _connect(settings) as connection:
        if _has_table(connection, "projects"):
            rows = connection.execute(
                """SELECT p.slug,p.name,p.summary,COUNT(DISTINCT cp.conversation_id) AS conversations,
                          COUNT(DISTINCT ki.id) AS knowledge_items
                   FROM projects p
                   LEFT JOIN conversation_projects cp ON cp.project_slug=p.slug
                   LEFT JOIN knowledge_items ki ON ki.project_slug=p.slug
                   GROUP BY p.slug,p.name,p.summary ORDER BY p.name COLLATE NOCASE"""
            ).fetchall()
            return [dict(row) for row in rows]
        names: dict[str, int] = {}
        for row in connection.execute("SELECT projects_json FROM analyses WHERE identity='LAKOTA'"):
            for project in json.loads(row[0]):
                names[project] = names.get(project, 0) + 1
        return [
            {"slug": name, "name": name, "summary": "", "conversations": count, "knowledge_items": 0}
            for name, count in sorted(names.items(), key=lambda item: item[0].lower())
        ]


def search(
    settings: Settings,
    query: str,
    project: str | None = None,
    category: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with _connect(settings) as connection:
        if _has_table(connection, "knowledge_items"):
            project = _resolve_project(connection, project)
            clauses = ["knowledge_items_fts MATCH ?"]
            params: list[object] = [query]
            if project:
                clauses.append("ki.project_slug=?")
                params.append(project)
            if category:
                clauses.append("ki.category=?")
                params.append(category)
            params.append(limit)
            rows = connection.execute(
                f"""SELECT ki.project_slug,ki.category,ki.title,ki.statement,ki.evidence,
                           ki.status,ki.confidence,ki.source_conversation_id,c.title AS conversation_title,c.created_at
                    FROM knowledge_items_fts
                    JOIN knowledge_items ki ON ki.id=knowledge_items_fts.rowid
                    JOIN conversations c ON c.conversation_id=ki.source_conversation_id
                    WHERE {' AND '.join(clauses)} ORDER BY rank LIMIT ?""",
                params,
            ).fetchall()
            return [dict(row) for row in rows]

        needle = f"%{query}%"
        rows = connection.execute(
            """SELECT pf.project AS project_slug,pf.category,'' AS title,pf.statement,pf.evidence,
                      pf.temporal_status AS status,pf.confidence,pf.source_conversation_id,
                      c.title AS conversation_title,c.created_at
               FROM project_facts pf JOIN conversations c
                 ON c.conversation_id=pf.source_conversation_id
               WHERE (pf.statement LIKE ? OR pf.evidence LIKE ?)
                 AND (? IS NULL OR pf.project=?) AND (? IS NULL OR pf.category=?)
               ORDER BY c.created_at DESC LIMIT ?""",
            (needle, needle, project, project, category, category, limit),
        ).fetchall()
        return [dict(row) for row in rows]


def errors(settings: Settings, project: str | None = None, limit: int = 50) -> list[dict[str, object]]:
    terms = "error OR failure OR failed OR bug OR broken OR issue"
    try:
        return search(settings, terms, project=project, category="error", limit=limit)
    except sqlite3.OperationalError:
        results: list[dict[str, object]] = []
        for category in ("known_issue", "failed_approach"):
            results.extend(search(settings, "*", project=project, category=category, limit=limit))
        return results[:limit]


def _has_table(connection: sqlite3.Connection, name: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=?", (name,)
    ).fetchone() is not None


def _resolve_project(connection: sqlite3.Connection, project: str | None) -> str | None:
    if not project:
        return None
    row = connection.execute(
        "SELECT slug FROM projects WHERE slug=? OR name=? COLLATE NOCASE LIMIT 1",
        (project, project),
    ).fetchone()
    return row[0] if row else project
