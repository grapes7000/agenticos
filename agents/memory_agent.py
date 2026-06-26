#!/usr/bin/env python3
import sqlite3, datetime
from agentos_common import DB_PATH, ensure_db, write_note, md_frontmatter, ollama_generate, log_event


def main():
    con = ensure_db()
    rows = con.execute("SELECT ts, kind, title, body FROM events ORDER BY id DESC LIMIT 50").fetchall()
    con.close()
    date = datetime.date.today().isoformat()
    raw = "\n".join([f"- {ts} [{kind}] {title}: {body}" for ts, kind, title, body in rows])
    prompt = """
Turn these Agentic OS event logs into a practical memory note.
Include:
- What worked
- What failed or needs attention
- Reusable lessons
- Next improvements
Do not invent events that are not in the logs.
""".strip() + "\n\n" + raw
    summary = ollama_generate(prompt)
    body = md_frontmatter(f"Agentic OS Memory {date}", ["agentic-os", "memory", "learning"])
    body += f"# Agentic OS Memory — {date}\n\n"
    body += summary + "\n\n## Raw Recent Events\n\n" + raw + "\n"
    note = write_note(f"Agentic OS/05 Memory/memory-{date}.md", body)
    log_event("memory", "Memory note created", str(note), {})
    print(f"Saved memory note: {note}")

if __name__ == "__main__":
    main()
