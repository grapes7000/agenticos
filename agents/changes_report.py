from pathlib import Path
from datetime import date
import difflib
import os
import sqlite3

try:
    from agents.note_policy import frontmatter, latest_note_name
except ModuleNotFoundError:
    from note_policy import frontmatter, latest_note_name

TODAY = date.today().isoformat()
HOME = Path.home()
VAULT = Path(os.getenv("OBSIDIAN_VAULT", str(HOME / "vault"))).expanduser()
OUT_DIR = VAULT / "Agentic OS" / "Change Reports"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DB = Path("data/db/agent_os.sqlite")

WATCH_DIRS = {
    "File Butler Plans": VAULT / "Agentic OS" / "File Plans",
    "Daily Briefings": VAULT / "Agentic OS" / "Daily Briefings",
    "Operator Reports": VAULT / "Agentic OS" / "Operator Reports",
    "Memory Digests": VAULT / "Agentic OS" / "Memory Digests",
    "Research Notes": VAULT / "Agentic OS" / "Research",
}

def md_files(folder: Path):
    if not folder.exists():
        return []
    return sorted(folder.glob("*.md"), key=lambda p: p.stat().st_mtime)

def read_limited(path: Path, limit=12000):
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        return text[:limit]
    except Exception as e:
        return f"Could not read {path}: {e}"

def diff_pair(old: Path, new: Path):
    old_text = read_limited(old).splitlines()
    new_text = read_limited(new).splitlines()

    diff = list(difflib.unified_diff(
        old_text,
        new_text,
        fromfile=old.name,
        tofile=new.name,
        lineterm=""
    ))

    if not diff:
        return ["No text differences detected."]

    # Keep report readable
    return diff[:220]

def db_status():
    lines = []

    if not DB.exists():
        return ["- Database missing."]

    try:
        with sqlite3.connect(DB) as con:
            file_count = con.execute("SELECT COUNT(*) FROM files").fetchone()[0]
            sensitive_count = con.execute("SELECT COUNT(*) FROM files WHERE sensitive = 1").fetchone()[0]
            lesson_count = con.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]

            lines.append(f"- Indexed files: **{file_count}**")
            lines.append(f"- Sensitive-looking files flagged: **{sensitive_count}**")
            lines.append(f"- Lessons stored: **{lesson_count}**")
            lines.append("")

            rows = con.execute(
                """
                SELECT category, COUNT(*)
                FROM files
                GROUP BY category
                ORDER BY COUNT(*) DESC, category
                """
            ).fetchall()

            lines.append("### Files By Category")
            lines.append("")

            if rows:
                for category, count in rows:
                    lines.append(f"- **{category or 'Uncategorized'}:** {count}")
            else:
                lines.append("- No files indexed yet.")

    except Exception as e:
        lines.append(f"- Database check failed: `{e}`")

    return lines

def latest_summary():
    lines = []

    for label, folder in WATCH_DIRS.items():
        files = md_files(folder)
        lines.append(f"### {label}")
        lines.append("")

        if not files:
            lines.append("- No notes found.")
            lines.append("")
            continue

        newest = files[-1]
        lines.append(f"- Latest: `{newest}`")
        lines.append(f"- Count: **{len(files)}**")

        if len(files) >= 2:
            previous = files[-2]
            lines.append(f"- Compared against: `{previous.name}`")
        else:
            lines.append("- No previous note to compare yet.")

        lines.append("")

    return lines

def comparisons():
    lines = []

    for label, folder in WATCH_DIRS.items():
        files = md_files(folder)

        lines.append(f"## Diff: {label}")
        lines.append("")

        if len(files) < 2:
            lines.append("Not enough notes to compare yet.")
            lines.append("")
            continue

        old, new = files[-2], files[-1]
        lines.append(f"Comparing `{old.name}` → `{new.name}`")
        lines.append("")
        lines.append("```diff")
        lines.extend(diff_pair(old, new))
        lines.append("```")
        lines.append("")

    return lines

out = OUT_DIR / latest_note_name("AI-LEARN", "Change Report")

lines = [
    *frontmatter(
        title=f"AI-LEARN: AgenticOS Change Report - {TODAY}",
        audience="ai_future",
        tags=["agentic-os", "changes", "report", "ai-learn"],
        purpose="Latest machine-readable summary of generated AgenticOS note deltas.",
    ),
    "",
    f"# AI-LEARN: AgenticOS Change Report - {TODAY}",
    "",
    "## Summary",
    "",
    "This report compares the latest AgenticOS notes and checks the current SQLite memory database.",
    "",
    "Important: this does not yet track true file-by-file history over time. It compares generated notes. A later snapshot layer can track exact new, changed, and deleted files.",
    "",
    "## Database Status",
    "",
    *db_status(),
    "",
    "## Latest Notes",
    "",
    *latest_summary(),
    "",
    *comparisons(),
    "## Suggested Next Actions",
    "",
    "- Review the newest File Butler plan.",
    "- Review the newest Daily Briefing.",
    "- Add anything useful into Lessons/Memory.",
    "- Keep move/delete actions manual until the approval layer exists.",
    "",
]

out.write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote change report: {out}")
