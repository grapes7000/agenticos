from pathlib import Path
import os
import shutil
import sqlite3
import urllib.request

ROOT = Path(os.getenv("AGENTOS_HOME", Path.home() / "AgenticOS")).expanduser()
VAULT = Path(os.getenv("OBSIDIAN_VAULT", Path.home() / "vault")).expanduser()
DB = ROOT / "data/db/agent_os.sqlite"

def check(label, ok, detail=""):
    mark = "✅" if ok else "❌"
    print(f"{mark} {label}{(': ' + detail) if detail else ''}")

print("AgenticOS Doctor")
print("================")
check("AgenticOS folder", ROOT.exists(), str(ROOT))
check("Obsidian vault", VAULT.exists(), str(VAULT))
check("Database file", DB.exists(), str(DB))

if DB.exists():
    try:
        with sqlite3.connect(DB) as con:
            tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for name in ["files", "actions", "lessons", "runs", "research_sources", "settings"]:
                check(f"DB table {name}", name in tables)
    except Exception as e:
        check("Database readable", False, str(e))

for cmd in ["python3", "ollama", "qwen", "hermes"]:
    check(f"Command {cmd}", shutil.which(cmd) is not None, shutil.which(cmd) or "not found")

try:
    with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as r:
        check("Ollama API", r.status == 200, "http://localhost:11434")
except Exception as e:
    check("Ollama API", False, str(e))

print("\nNext useful tests:")
print("  agentos scan")
print("  agentos files")
print("  agentos briefing")
print("  agentos lesson add \"Test lesson\" \"Layer installed successfully.\"")
