from pathlib import Path
from html.parser import HTMLParser
from datetime import datetime, date
import argparse
import os
import re
import sqlite3
import urllib.request
from urllib.parse import urlparse

DB = Path("data/db/agent_os.sqlite")
VAULT = Path(os.getenv("OBSIDIAN_VAULT", str(Path.home() / "vault"))).expanduser()
OUT_DIR = VAULT / "Agentic OS" / "Research"
OUT_DIR.mkdir(parents=True, exist_ok=True)

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = False
        self.title = ""
        self.in_title = False
    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.skip = True
        if tag == "title":
            self.in_title = True
    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"}:
            self.skip = False
        if tag == "title":
            self.in_title = False
    def handle_data(self, data):
        text = " ".join(data.split())
        if not text:
            return
        if self.in_title:
            self.title += text
        elif not self.skip:
            self.parts.append(text)

def fetch(url: str) -> tuple[str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "AgenticOS-Research/0.2"})
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read()
        content_type = r.headers.get("content-type", "")
    if "text/html" in content_type or url.lower().endswith((".html", "/")):
        parser = TextExtractor()
        parser.feed(raw.decode("utf-8", errors="ignore"))
        return parser.title.strip() or urlparse(url).netloc, "\n".join(parser.parts)
    return urlparse(url).path.split("/")[-1] or url, raw.decode("utf-8", errors="ignore")

def safe_name(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9 _-]+", "", text).strip()
    return (text[:90] or "Research Note").replace("  ", " ")

def summarize(text: str) -> str:
    clipped = text[:8000]
    try:
        from tools.local_llm import generate
        return generate(
            "Summarize this source for an AgenticOS Obsidian research note. Include key points, why it matters, and follow-up questions.\n\n" + clipped,
            timeout=180,
        )
    except Exception as e:
        basic = clipped[:1200]
        return f"Local LLM summary unavailable: `{e}`\n\nRaw excerpt:\n\n{basic}"

def save_research(url: str, use_llm: bool = True):
    title, text = fetch(url)
    summary = summarize(text) if use_llm else text[:1500]
    stamp = date.today().isoformat()
    out = OUT_DIR / f"{stamp} - {safe_name(title)}.md"
    lines = [
        "---",
        "tags: [agentic-os, research]",
        f"created: {datetime.now().isoformat(timespec='seconds')}",
        f"source_url: {url}",
        "---",
        "",
        f"# {title}",
        "",
        f"Source: {url}",
        "",
        "## Summary",
        "",
        summary,
        "",
        "## Follow-up Questions",
        "",
        "- What should AgenticOS remember from this?",
        "- Is there a reusable skill or workflow hidden in this?",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")
    if DB.exists():
        with sqlite3.connect(DB) as con:
            con.execute(
                "INSERT OR REPLACE INTO research_sources(url, title, summary, note_path, fetched_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (url, title, summary[:4000], str(out)),
            )
    print(f"Wrote research note: {out}")

parser = argparse.ArgumentParser(description="Save a web page as an AgenticOS Obsidian research note")
parser.add_argument("url")
parser.add_argument("--no-llm", action="store_true")
args = parser.parse_args()
save_research(args.url, use_llm=not args.no_llm)
