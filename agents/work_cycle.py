from pathlib import Path
from datetime import datetime, date
import json
import os
import subprocess
import urllib.request

HOME = Path.home()
ROOT = HOME / "AgenticOS"
VAULT = Path(os.getenv("OBSIDIAN_VAULT", str(HOME / "vault"))).expanduser()
MODEL = os.getenv("AGENTOS_MODEL", "qwen2.5-coder:7b")
STAMP = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
TODAY = date.today().isoformat()
WORK_DIR = VAULT / "Agentic OS" / "Work Cycles"
PATCH_DIR = VAULT / "Agentic OS" / "Patch Plans"
WORK_DIR.mkdir(parents=True, exist_ok=True)
PATCH_DIR.mkdir(parents=True, exist_ok=True)

SAFE_RULES = """
- Do not apply fixes automatically.
- Do not delete files.
- Do not move user files.
- Do not touch wallets, private keys, browser profiles, banking files, SSH keys, browser cookies, or secrets.
- Do not use sudo.
- Pick only one small, low-risk improvement.
- Prefer bug fixes, safer paths, better help text, better error handling, better tests, or better report formatting.
"""

def run_cmd(cmd, timeout=180):
    try:
        r = subprocess.run(cmd, cwd=ROOT, text=True, shell=True, capture_output=True, timeout=timeout, check=False)
        return f"$ {cmd}\nRETURN CODE: {r.returncode}\n\nSTDOUT:\n{r.stdout[-6000:]}\n\nSTDERR:\n{r.stderr[-6000:]}"
    except Exception as e:
        return f"$ {cmd}\nFAILED: {e}"

def list_files():
    lines = []
    for folder in ["agents", "tools", "scripts", "bin"]:
        base = ROOT / folder
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if p.is_file():
                lines.append(f"- {p.relative_to(ROOT)}")
    return "\n".join(lines) or "- No files found."

def source_samples(max_chars=18000):
    chunks = []
    used = 0
    for folder in ["agents", "tools", "scripts", "bin"]:
        base = ROOT / folder
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file() or p.name.endswith(".sqlite"):
                continue
            if p.suffix.lower() not in [".py", ".sh", ".md", ".json", ""]:
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")[:2500]
            except Exception:
                continue
            block = f"\n\n## FILE: {p.relative_to(ROOT)}\n\n```text\n{text}\n```"
            if used + len(block) > max_chars:
                return "".join(chunks)
            chunks.append(block)
            used += len(block)
    return "".join(chunks)

def ask_ollama(prompt):
    payload = {"model": MODEL, "prompt": prompt, "stream": False, "options": {"temperature": 0.2, "num_predict": 2200}}
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=240) as res:
        data = json.loads(res.read().decode("utf-8"))
    return data.get("response", "").strip()

context = f"""
# AgenticOS Work Cycle Context

Date: {TODAY}
Run ID: {STAMP}
Root: {ROOT}
Vault: {VAULT}
Model: {MODEL}

## Safety Rules

{SAFE_RULES}

## Project Files

{list_files()}

## agentos doctor

```text
{run_cmd('agentos doctor')}
```

## agentos test

```text
{run_cmd('agentos test')}
```

## agentos fix-status

```text
{run_cmd('agentos fix-status')}
```

## Source Samples

{source_samples()}
"""

prompt = f"""
You are the AgenticOS Iterative Project Worker.

Do one safe work cycle. Review the context, pick exactly one small bug or improvement, and create a patch plan only.

Write Markdown with these sections:

# AgenticOS Work Cycle - {STAMP}

## Verdict
## Chosen Task
## Why This Task
## Risk Level
## Proposed Fix Plan
## Files To Inspect Or Edit
## Test Plan
## Stop Conditions
## Next Cycle Suggestion

Never claim you applied changes. Never suggest risky file operations. Never suggest touching private keys, wallets, browser profiles, banking files, or secrets.

Context:

{context}
"""

try:
    report = ask_ollama(prompt)
except Exception as e:
    report = f"""# AgenticOS Work Cycle - {STAMP}

## Verdict

The work-cycle runner started, but local Qwen/Ollama was not available.

## Chosen Task

Fix local model availability before using AI work cycles.

## Why This Task

The script could not call Ollama successfully.

## Risk Level

Low

## Proposed Fix Plan

```bash
ollama serve
ollama pull qwen2.5-coder:7b
ollama run qwen2.5-coder:7b
agentos work-cycle
```

## Files To Inspect Or Edit

- No project files need editing yet.

## Test Plan

```bash
curl http://localhost:11434/api/tags
ollama list
agentos work-cycle
```

## Stop Conditions

- Stop if Ollama is not installed.
- Stop if the model cannot be pulled.
- Stop if the computer becomes too slow.

## Next Cycle Suggestion

After Ollama/Qwen works, rerun the work cycle and let it inspect AgenticOS for one small improvement.

## Error

`{e}`

No fixes were applied automatically.
"""

work_file = WORK_DIR / f"{STAMP} Work Cycle.md"
patch_file = PATCH_DIR / f"{STAMP} Patch Plan.md"
work_file.write_text(report + "\n", encoding="utf-8")
patch_file.write_text(f"""---
tags: [agentic-os, work-cycle, patch-plan]
created: {TODAY}
run_id: {STAMP}
---

# Patch Plan - {STAMP}

This is a proposal only. Nothing was applied automatically.

{report}
""", encoding="utf-8")
print(f"Wrote work cycle: {work_file}")
print(f"Wrote patch plan: {patch_file}")
print("No fixes were applied automatically.")
