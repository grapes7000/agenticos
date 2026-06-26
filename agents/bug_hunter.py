from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import os
import subprocess
import urllib.request

HOME = Path.home()
AGENTOS = Path(os.getenv("AGENTOS_DIR", str(HOME / "AgenticOS"))).expanduser()
VAULT = Path(os.getenv("OBSIDIAN_VAULT", str(HOME / "vault"))).expanduser()
MODEL = os.getenv("AGENTOS_MODEL", "qwen2.5-coder:7b")
STAMP = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
OUT_DIR = VAULT / "Agentic OS" / "Bug Reports"
OUT_DIR.mkdir(parents=True, exist_ok=True)
BUG_DIR = AGENTOS / "bugs"
BUG_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_CHARS = 12000
MAX_TOTAL_CHARS = 80000

SYSTEM_PROMPT = """
You are AgenticOS Bug Hunter, a careful local QA/code review agent.

Your job is to look for bugs, missing folders, broken CLI routing, unsafe shell patterns,
fragile assumptions, scripts that fail when optional tools are missing, and places where
AgenticOS could accidentally modify user files.

Rules:
- Do not suggest deleting files.
- Do not suggest touching wallets, SSH keys, browser cookies, bank files, or credentials.
- Prefer safe fixes: mkdir -p, existence checks, dry-run defaults, backups, explicit paths.
- If proposing code changes, keep them small.
- Always include exact commands when useful.
- Mark severity as Critical, High, Medium, Low, or Nice-to-have.
- Separate confirmed bugs from guesses.

Write Markdown with sections:
# AgenticOS Bug Hunt Report
## Executive Summary
## Confirmed Bugs
## Likely Bugs / Fragile Areas
## Safety Concerns
## Suggested Fix Order
## Exact Commands To Inspect
## Patch Ideas For Later Review
""".strip()

def run_cmd(cmd, timeout=45):
    try:
        p = subprocess.run(cmd, cwd=str(AGENTOS), text=True, capture_output=True, timeout=timeout)
        return f"$ {' '.join(cmd)}\nEXIT {p.returncode}\nSTDOUT:\n{p.stdout[:4000]}\nSTDERR:\n{p.stderr[:4000]}"
    except Exception as e:
        return f"$ {' '.join(cmd)}\nERROR: {e}"

def read_file(path: Path, limit=MAX_FILE_CHARS):
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        return text[:limit]
    except Exception as e:
        return f"Could not read: {e}"

def collect_context():
    parts = []
    parts.append(f"AgenticOS path: {AGENTOS}")
    parts.append(f"Vault path: {VAULT}")
    parts.append(f"Model: {MODEL}")
    parts.append("\n## Command outputs\n")
    for cmd in [
        ["pwd"],
        ["find", ".", "-maxdepth", "3", "-type", "f"],
        ["ls", "-lah", "bin"],
        ["ls", "-lah", "agents"],
        ["ls", "-lah", "tools"],
    ]:
        parts.append("```text\n" + run_cmd(cmd) + "\n```")

    latest_reports = [
        VAULT / "Agentic OS" / "Test Reports" / "latest System Test Report.md",
        AGENTOS / "logs" / "system-test-latest.md",
    ]
    for p in latest_reports:
        if p.exists():
            parts.append(f"\n## Latest report: {p}\n```markdown\n{read_file(p, 20000)}\n```")

    source_dirs = [AGENTOS / "bin", AGENTOS / "agents", AGENTOS / "tools", AGENTOS / "scripts"]
    parts.append("\n## Source snippets\n")
    for folder in source_dirs:
        if not folder.exists():
            continue
        for path in sorted(folder.rglob("*")):
            if not path.is_file():
                continue
            if path.stat().st_size > 300_000:
                continue
            if path.suffix not in {".py", ".sh", "", ".md"} and path.parent.name != "bin":
                continue
            rel = path.relative_to(AGENTOS)
            parts.append(f"\n### {rel}\n```text\n{read_file(path)}\n```")
            if sum(len(x) for x in parts) > MAX_TOTAL_CHARS:
                parts.append("\n[Context truncated to keep local model prompt manageable.]\n")
                return "\n".join(parts)
    return "\n".join(parts)

def ask_ollama(prompt: str):
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.18, "num_predict": 2500},
    }
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=240) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("response", "").strip()

def fallback_report(context: str, error: Exception):
    return f"""# AgenticOS Bug Hunt Report - Fallback

## Executive Summary

The Qwen/Ollama bug-hunter call failed, so this is a static fallback report.

## Ollama Error

`{error}`

## Likely Things To Check

1. Run `agentos test` and open the newest Test Report.
2. Check whether `ollama serve` is running.
3. Check whether `{MODEL}` is installed with `ollama list`.
4. Check whether `~/AgenticOS/bin/agentos` contains branches for the commands you expect.
5. Check whether all scripts create parent folders before writing files.
6. Check whether optional tools like Hermes/OpenClaw/Qwen fail gracefully when missing.

## Useful Commands

```bash
cd ~/AgenticOS
agentos test
ollama list
hermes cron list
ls -lah ~/AgenticOS/bin
ls -lah ~/AgenticOS/agents
```

## Context Collected

```text
{context[:20000]}
```
"""

def main():
    context = collect_context()
    prompt = SYSTEM_PROMPT + "\n\nContext to review:\n\n" + context
    try:
        report = ask_ollama(prompt)
        if not report:
            raise RuntimeError("Ollama returned an empty response")
    except Exception as e:
        report = fallback_report(context, e)

    out = OUT_DIR / f"{STAMP} Bug Hunt Report.md"
    latest = OUT_DIR / "latest Bug Hunt Report.md"
    local = BUG_DIR / f"{STAMP}-bug-hunt.md"
    for p in [out, latest, local]:
        p.write_text(report + "\n", encoding="utf-8")
    print(f"Wrote bug hunt report: {out}")
    print(f"Latest bug hunt report: {latest}")

if __name__ == "__main__":
    main()
