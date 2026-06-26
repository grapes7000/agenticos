from pathlib import Path
from datetime import date, datetime
import os
import sqlite3

try:
    from agents.note_policy import frontmatter, latest_note_name
except ModuleNotFoundError:
    from note_policy import frontmatter, latest_note_name

DB = Path("data/db/agent_os.sqlite")
VAULT = Path(os.getenv("OBSIDIAN_VAULT", str(Path.home() / "vault"))).expanduser()
OUT_DIR = VAULT / "Agentic OS" / "Memory Digests"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def latest_lessons(limit=20):
    if not DB.exists():
        return []
    with sqlite3.connect(DB) as con:
        return con.execute("SELECT title, body, source, created_at FROM lessons ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

def db_counts():
    counts = {}
    if not DB.exists():
        return counts
    with sqlite3.connect(DB) as con:
        for table in ["files", "lessons", "research_sources", "actions", "runs"]:
            try:
                counts[table] = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except Exception:
                counts[table] = "?"
    return counts

stamp = date.today().isoformat()
out = OUT_DIR / latest_note_name("AI-LEARN", "Memory Digest")
counts = db_counts()
lessons = latest_lessons()

lines = [
    *frontmatter(
        title=f"AI-LEARN: Memory Digest - {stamp}",
        audience="ai_future",
        tags=["agentic-os", "memory-digest", "ai-learn"],
        purpose="Compact reusable AgenticOS memory/database summary for future AI agents.",
    ),
    "",
    f"# AI-LEARN: Memory Digest - {stamp}",
    "",
    "## System Counts",
    "",
]
for k, v in counts.items():
    lines.append(f"- {k}: **{v}**")
lines += ["", "## Recent Lessons", ""]
if not lessons:
    lines.append("- No lessons yet. Add one with `agentos lesson add \"Title\" \"Body\"`.")
else:
    for title, body, source, created in lessons:
        lines.append(f"### {title}")
        lines.append(f"- Source: `{source}`")
        lines.append(f"- Created: `{created}`")
        lines.append("")
        lines.append(body)
        lines.append("")
lines += [
    "## Rules To Preserve",
    "",
    "- File actions stay dry-run until explicitly approved by the user.",
    "- Never touch wallets, seed phrases, private keys, or bank credentials.",
    "- Markdown must be AI-LEARN or READ-ME; raw/repetitive data belongs in SQLite/JSON/TXT.",
    "- Log what changed and why.",
]
out.write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote memory digest: {out}")
