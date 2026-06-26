from pathlib import Path
from datetime import date
import json
import os
import subprocess
import urllib.request

TODAY = date.today().isoformat()
VAULT = Path(os.getenv("OBSIDIAN_VAULT", str(Path.home() / "vault"))).expanduser()
OUT_DIR = VAULT / "Agentic OS" / "Operator Reports"
OUT_DIR.mkdir(parents=True, exist_ok=True)

try:
    from agents.note_policy import frontmatter, latest_note_name
except ModuleNotFoundError:
    from note_policy import latest_note_name

MODEL = os.getenv("AGENTOS_MODEL", "qwen2.5-coder:7b")

def get_context():
    result = subprocess.run(
        [str(Path.home() / "AgenticOS" / "scripts" / "operator_context.sh")],
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout + "\n\nSTDERR:\n" + result.stderr

def ask_ollama(prompt):
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.25,
            "num_predict": 1800
        }
    }

    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(req, timeout=180) as response:
        data = json.loads(response.read().decode("utf-8"))

    return data.get("response", "").strip()

context = get_context()

prompt = f"""
You are the AgenticOS Operator.

Your job:
- Read the system context.
- Summarize what happened.
- Detect problems.
- Suggest the next safest actions.
- Keep everything practical.
- Never recommend deleting, moving, overwriting, trading, wallet access, or banking access.
- If something needs fixing, give exact commands.
- Assume this is a Linux Mint desktop using Ollama, Hermes, Qwen, SQLite, and Obsidian.

Write a clean Markdown operator report with these sections:

# READ-ME: AgenticOS Operator Report - {TODAY}

## Status
## What Worked
## Problems or Warnings
## Best Next Actions
## Commands To Run
## Notes For Memory

System context:
{context}
"""

try:
    report = ask_ollama(prompt)
except Exception as e:
    report = f"""# READ-ME: AgenticOS Operator Report - {TODAY}

## Status

Operator report failed.

## Error

`{e}`

## Best Next Actions

- Make sure Ollama is running.
- Make sure the model is installed with: `ollama pull qwen2.5-coder:7b`
- Test with: `ollama run qwen2.5-coder:7b`
"""

out = OUT_DIR / latest_note_name("READ-ME", "Operator Report")
out.write_text(report + "\n", encoding="utf-8")

print(f"Wrote operator report: {out}")
