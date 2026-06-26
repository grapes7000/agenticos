#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, date
from pathlib import Path
import json
import os
import urllib.request

HOME = Path.home()
VAULT = Path(os.getenv("OBSIDIAN_VAULT", str(HOME / "vault"))).expanduser()
MODEL = os.getenv("AGENTOS_MODEL", "qwen2.5-coder:7b")
TODAY = date.today().isoformat()
STAMP = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
OUT_DIR = VAULT / "Agentic OS" / "Security Summaries"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def latest(folder: Path, pattern: str = "*.md") -> Path | None:
    if not folder.exists():
        return None
    files = sorted(folder.glob(pattern), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def read(path: Path | None, limit: int = 50000) -> str:
    if path is None:
        return "No file found."
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        return f"FILE: {path}\n\n" + text[:limit]
    except Exception as e:
        return f"Could not read {path}: {e}"


def ask_ollama(prompt: str) -> str:
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.18,
            "num_predict": 2600,
        },
    }
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=240) as res:
        data = json.loads(res.read().decode("utf-8"))
    return data.get("response", "").strip()


security_file = latest(VAULT / "Agentic OS" / "Security Reports")
build_file = latest(VAULT / "Agentic OS" / "Build Quality Reports")
health_file = latest(VAULT / "Agentic OS" / "Health") or latest(VAULT / "Agentic OS" / "Health Reports")

security_text = read(security_file)
build_text = read(build_file)
health_text = read(health_file, limit=20000)

prompt = f"""
You are the AgenticOS Security and Build Quality Reviewer.

You are reviewing local security/build reports from a Linux Mint desktop that has AgenticOS, Hermes, OpenClaw, Ollama/Qwen, Docker services, SearXNG, and Obsidian reports.

Rules:
- Be practical and plain-English.
- Do not panic about scanner warnings; label them as investigate/review unless clearly severe.
- Do not recommend exposing OpenClaw publicly.
- Do not recommend touching wallets, browser cookies, SSH keys, private keys, or bank files.
- Do not suggest destructive commands.
- Focus on: open ports, failed services, Docker exposure, OpenClaw permissions, Hermes jobs, AgenticOS script quality, disk/memory, and next safest fixes.
- If data is missing, say what report/command is missing.

Write a Markdown report with these exact sections:

# Security + Build Quality Summary - {STAMP}

## Overall Verdict
## What Looks Healthy
## What Looks Risky Or Needs Review
## Network Exposure
## OpenClaw / Hermes Safety
## AgenticOS Build Quality
## Top 5 Next Fixes
## Commands To Run Next
## What Not To Do Yet

Security report:
{security_text}

Build quality report:
{build_text}

Health report:
{health_text}
"""

try:
    summary = ask_ollama(prompt)
except Exception as e:
    summary = f"""# Security + Build Quality Summary - {STAMP}

## Overall Verdict

Could not use local Ollama/Qwen to summarize the reports.

## Error

`{e}`

## Reports To Review Manually

- Security report: `{security_file}`
- Build quality report: `{build_file}`
- Health report: `{health_file}`

## Commands To Run Next

```bash
ollama serve
ollama pull qwen2.5-coder:7b
agentos security-summary
```
"""

out = OUT_DIR / f"{STAMP} Security Build Summary.md"
out.write_text(summary + "\n", encoding="utf-8")
print(summary)
print(f"\nWrote security summary: {out}")
