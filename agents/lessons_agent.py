from pathlib import Path
import argparse
import os
import sqlite3
from datetime import datetime, date

DB = Path("data/db/agent_os.sqlite")
VAULT = Path(os.getenv("OBSIDIAN_VAULT", str(Path.home() / "vault"))).expanduser()
LESSON_DIR = VAULT / "Agentic OS" / "Lessons"
LESSON_DIR.mkdir(parents=True, exist_ok=True)

def ensure_db():
    if not DB.exists():
        raise SystemExit("Database not found. Run: agentos init-db")

def safe_name(text: str) -> str:
    keep = "".join(c if c.isalnum() or c in " -_" else "" for c in text).strip()
    return keep[:80].replace("  ", " ") or "Lesson"

def add_lesson(title: str, body: str, source: str = "manual", tags: str = ""):
    ensure_db()
    with sqlite3.connect(DB) as con:
        cur = con.execute(
            "INSERT INTO lessons(title, body, source, tags) VALUES (?, ?, ?, ?)",
            (title, body, source, tags),
        )
        lesson_id = cur.lastrowid
    stamp = date.today().isoformat()
    out = LESSON_DIR / f"{stamp} - {safe_name(title)}.md"
    lines = [
        "---",
        "tags: [agentic-os, lesson]" + (f" # {tags}" if False else ""),
        f"created: {datetime.now().isoformat(timespec='seconds')}",
        f"source: {source}",
        f"lesson_id: {lesson_id}",
        "---",
        "",
        f"# {title}",
        "",
        body,
        "",
        "## Why this matters",
        "",
        "- This lesson should help AgenticOS avoid repeating mistakes or improve future runs.",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Added lesson #{lesson_id}: {title}")
    print(f"Wrote: {out}")

def list_lessons(limit: int = 20):
    ensure_db()
    with sqlite3.connect(DB) as con:
        rows = con.execute(
            "SELECT id, title, source, created_at FROM lessons ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    for row in rows:
        print(f"#{row[0]} {row[1]} [{row[2]}] {row[3]}")

def export_lessons():
    ensure_db()
    out = LESSON_DIR / f"{date.today().isoformat()} Lessons Index.md"
    with sqlite3.connect(DB) as con:
        rows = con.execute("SELECT id, title, body, source, tags, created_at FROM lessons ORDER BY id DESC").fetchall()
    lines = ["# AgenticOS Lessons Index", "", f"Exported: {datetime.now().isoformat(timespec='seconds')}", ""]
    for lesson_id, title, body, source, tags, created in rows:
        lines += [f"## #{lesson_id} - {title}", "", f"- Source: `{source}`", f"- Created: `{created}`", "", body, ""]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Exported lessons to: {out}")

parser = argparse.ArgumentParser(description="AgenticOS lessons/memory agent")
sub = parser.add_subparsers(dest="cmd", required=True)
add = sub.add_parser("add")
add.add_argument("title")
add.add_argument("body")
add.add_argument("--source", default="manual")
add.add_argument("--tags", default="")
ls = sub.add_parser("list")
ls.add_argument("--limit", type=int, default=20)
sub.add_parser("export")
args = parser.parse_args()

if args.cmd == "add":
    add_lesson(args.title, args.body, args.source, args.tags)
elif args.cmd == "list":
    list_lessons(args.limit)
elif args.cmd == "export":
    export_lessons()
