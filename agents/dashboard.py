from pathlib import Path
from datetime import datetime
import os
import sqlite3
import html

ROOT = Path(os.getenv("AGENTOS_HOME", Path.home() / "AgenticOS")).expanduser()
VAULT = Path(os.getenv("OBSIDIAN_VAULT", Path.home() / "vault")).expanduser()
DB = ROOT / "data/db/agent_os.sqlite"
OUT = ROOT / "dashboard/index.html"
OUT.parent.mkdir(parents=True, exist_ok=True)

def count(table):
    if not DB.exists():
        return 0
    try:
        with sqlite3.connect(DB) as con:
            return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    except Exception:
        return "?"

sections = [
    ("Daily Briefings", VAULT / "Agentic OS" / "Daily Briefings"),
    ("File Plans", VAULT / "Agentic OS" / "File Plans"),
    ("Lessons", VAULT / "Agentic OS" / "Lessons"),
    ("Memory Digests", VAULT / "Agentic OS" / "Memory Digests"),
    ("Research", VAULT / "Agentic OS" / "Research"),
]

cards = "".join(f"<div class='card'><h2>{name}</h2><p>{count(table)} records</p></div>" for name, table in [("Files", "files"), ("Lessons", "lessons"), ("Research", "research_sources"), ("Runs", "runs")])
links = "".join(f"<li><strong>{html.escape(name)}</strong>: <code>{html.escape(str(path))}</code></li>" for name, path in sections)
html_doc = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>AgenticOS Dashboard</title>
<style>
body {{ font-family: system-ui, sans-serif; background:#111; color:#f5f5f5; margin:40px; }}
.grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(180px,1fr)); gap:16px; }}
.card {{ background:#1e1e1e; padding:18px; border:1px solid #333; border-radius:14px; }}
code {{ color:#ffb3df; }}
a {{ color:#ff8bd1; }}
</style></head><body>
<h1>AgenticOS Dashboard</h1>
<p>Generated: {datetime.now().isoformat(timespec='seconds')}</p>
<div class='grid'>{cards}</div>
<h2>Obsidian Locations</h2>
<ul>{links}</ul>
<h2>Safe Next Commands</h2>
<pre>agentos morning
agentos briefing
agentos files
agentos lesson list
agentos memory
agentos research https://example.com --no-llm</pre>
</body></html>"""
OUT.write_text(html_doc, encoding="utf-8")
print(f"Wrote dashboard: {OUT}")
