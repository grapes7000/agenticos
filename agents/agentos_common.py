import os, sqlite3, json, re, textwrap, datetime, pathlib
from typing import Any, Dict, List, Optional

try:
    import requests
except Exception:
    requests = None

ROOT = pathlib.Path(os.environ.get("AGENTOS_HOME", pathlib.Path.home() / "AgenticOS")).expanduser()
CONFIG = ROOT / "config" / "agentos.env"

def load_env() -> Dict[str, str]:
    env = {}
    if CONFIG.exists():
        for line in CONFIG.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            env[k.strip()] = os.path.expandvars(os.path.expanduser(v))
            os.environ.setdefault(k.strip(), env[k.strip()])
    return env

ENV = load_env()
AGENTOS_HOME = pathlib.Path(ENV.get("AGENTOS_HOME", str(ROOT))).expanduser()
VAULT = pathlib.Path(ENV.get("AGENTOS_VAULT", str(pathlib.Path.home() / "vault"))).expanduser()
MODEL = ENV.get("AGENTOS_MODEL", "qwen2.5-coder:7b")
OLLAMA_BASE_URL = ENV.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
DB_PATH = AGENTOS_HOME / "data" / "agentos.sqlite"


def now_slug() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def today() -> str:
    return datetime.date.today().isoformat()


def slugify(s: str, max_len: int = 80) -> str:
    s = re.sub(r"[^a-zA-Z0-9._ -]+", "", s).strip().replace(" ", "_")
    return s[:max_len] or "untitled"


def ensure_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""
    CREATE TABLE IF NOT EXISTS events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts TEXT NOT NULL,
      kind TEXT NOT NULL,
      title TEXT,
      body TEXT,
      meta_json TEXT
    )
    """)
    con.execute("""
    CREATE TABLE IF NOT EXISTS file_suggestions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts TEXT NOT NULL,
      path TEXT NOT NULL,
      suggested_action TEXT NOT NULL,
      reason TEXT,
      status TEXT DEFAULT 'dry_run'
    )
    """)
    con.commit()
    return con


def log_event(kind: str, title: str = "", body: str = "", meta: Optional[Dict[str, Any]] = None) -> None:
    con = ensure_db()
    con.execute(
        "INSERT INTO events (ts, kind, title, body, meta_json) VALUES (?, ?, ?, ?, ?)",
        (datetime.datetime.now().isoformat(timespec="seconds"), kind, title, body, json.dumps(meta or {})),
    )
    con.commit(); con.close()


def write_note(relative_path: str, content: str) -> pathlib.Path:
    path = VAULT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def ollama_generate(prompt: str, model: Optional[str] = None, timeout: int = 120) -> str:
    if requests is None:
        return ""
    model = model or MODEL
    try:
        r = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=timeout,
        )
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except Exception as e:
        return f"[Ollama unavailable or model failed: {e}]"


def md_frontmatter(title: str, tags: List[str] = None) -> str:
    tags = tags or []
    tag_lines = "\n".join([f"  - {t}" for t in tags])
    return f"---\ntitle: {title}\ncreated: {datetime.datetime.now().isoformat(timespec='seconds')}\ntags:\n{tag_lines}\n---\n\n"
