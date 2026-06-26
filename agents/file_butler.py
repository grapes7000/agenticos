from pathlib import Path
import sqlite3
from datetime import date
import os

DB = Path("data/db/agent_os.sqlite")
VAULT = Path(os.getenv("OBSIDIAN_VAULT", str(Path.home() / "vault"))).expanduser()
OUT_DIR = VAULT / "Agentic OS" / "File Plans"
OUT_DIR.mkdir(parents=True, exist_ok=True)

if not DB.exists():
    raise SystemExit("Database not found. Run: python3 tools/init_db.py")

with sqlite3.connect(DB) as con:
    rows = con.execute(
        """
        SELECT path, name, category, size_bytes, sensitive
        FROM files
        ORDER BY category, name
        LIMIT 1000
        """
    ).fetchall()

by_cat = {}
sensitive = []
for path, name, category, size, sens in rows:
    if sens:
        sensitive.append((path, name, category))
        continue
    by_cat.setdefault(category or "Other", []).append((path, name, size or 0))

stamp = date.today().isoformat()
out = OUT_DIR / f"{stamp} File Butler Dry Run.md"

lines = [
    "---",
    "tags: [agentic-os, file-butler, dry-run]",
    f"created: {stamp}",
    "---",
    "",
    f"# File Butler Dry Run - {stamp}",
    "",
    "## Safety Notice",
    "",
    "This is a dry-run plan. No files were moved, deleted, renamed, or edited.",
    "",
    "## Summary",
    "",
    f"- Non-sensitive indexed files shown: **{sum(len(v) for v in by_cat.values())}**",
    f"- Sensitive-looking files skipped: **{len(sensitive)}**",
    "",
    "## Proposed Review Buckets",
    "",
]

for cat, items in sorted(by_cat.items()):
    lines.append(f"### {cat}")
    lines.append("")
    for path, name, size in items[:75]:
        kb = round(size / 1024, 1)
        lines.append(f"- `{name}`")
        lines.append(f"  - Current path: `{path}`")
        lines.append(f"  - Size: {kb} KB")
        lines.append(f"  - Suggested action: review and maybe sort into `{cat}/`")
        lines.append("")

if sensitive:
    lines.extend([
        "## Sensitive-Looking Files Skipped",
        "",
        "These were not included in move suggestions because their names look private.",
        "",
    ])
    for path, name, cat in sensitive[:150]:
        lines.append(f"- `{name}`")
        lines.append(f"  - Path: `{path}`")
        lines.append("")

out.write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote dry-run plan: {out}")
