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
RUN_DIR = AGENTOS / "iterative-fixes" / "runs" / STAMP
RUN_DIR.mkdir(parents=True, exist_ok=True)
FIX_DIR = VAULT / "Agentic OS" / "Fix Cycles"
PATCH_DIR = VAULT / "Agentic OS" / "Patch Plans"
FIX_DIR.mkdir(parents=True, exist_ok=True)
PATCH_DIR.mkdir(parents=True, exist_ok=True)

def run(cmd, timeout=300):
    p = subprocess.run(cmd, cwd=str(AGENTOS), text=True, capture_output=True, timeout=timeout)
    text = f"$ {' '.join(cmd)}\nEXIT {p.returncode}\n\nSTDOUT:\n{p.stdout}\n\nSTDERR:\n{p.stderr}\n"
    return p.returncode, text

def read(path: Path, limit=30000):
    if not path.exists():
        return f"Missing: {path}"
    return path.read_text(encoding="utf-8", errors="replace")[:limit]

def ask_ollama(prompt: str):
    payload = {"model": MODEL, "prompt": prompt, "stream": False, "options": {"temperature": 0.16, "num_predict": 2500}}
    req = urllib.request.Request("http://localhost:11434/api/generate", data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as resp:
        return json.loads(resp.read().decode("utf-8")).get("response", "").strip()

def git_status():
    code, text = run(["git", "status", "--short"], timeout=30) if (AGENTOS / ".git").exists() else (1, "Git repo not initialized in AgenticOS.")
    return text

def main():
    timeline = []

    code, test_output = run(["python3", "agents/system_test_runner.py"], timeout=360)
    (RUN_DIR / "01-system-test-output.txt").write_text(test_output, encoding="utf-8")
    timeline.append(f"System tests exit code: {code}")

    code, bug_output = run(["python3", "agents/bug_hunter.py"], timeout=360)
    (RUN_DIR / "02-bug-hunter-output.txt").write_text(bug_output, encoding="utf-8")
    timeline.append(f"Bug hunter exit code: {code}")

    test_report = read(VAULT / "Agentic OS" / "Test Reports" / "latest System Test Report.md")
    bug_report = read(VAULT / "Agentic OS" / "Bug Reports" / "latest Bug Hunt Report.md")
    status = git_status()

    prompt = f"""
You are AgenticOS Iterative Fix Planner.

Create a patch plan, not an applied patch. The user wants safe iterative fixes.

Rules:
- Do not modify files directly.
- Do not suggest deleting user data.
- Do not suggest sudo.
- Focus on small fixes to AgenticOS scripts only.
- Prefer fixes that add mkdir -p, existence checks, clearer errors, better help text, or safer dry-run behavior.
- If a command should be run, include it in a review-only command block.
- Mark each suggested fix with risk: Low/Medium/High.
- Include a manual review checklist.

Inputs:

## Git Status
```text
{status[:8000]}
```

## System Test Report
```markdown
{test_report}
```

## Bug Hunt Report
```markdown
{bug_report}
```

Write Markdown with:
# AgenticOS Iterative Fix Plan - {STAMP}
## Top Priority Bugs
## Proposed Small Fixes
## Files Likely To Change
## Manual Commands To Review
## Do Not Touch
## Stop Conditions
## Next Cycle Prompt
"""
    try:
        plan = ask_ollama(prompt)
        if not plan:
            raise RuntimeError("empty response")
    except Exception as e:
        plan = f"""# AgenticOS Iterative Fix Plan - {STAMP}

## Status

Could not ask Ollama/Qwen for a fix plan.

## Error

`{e}`

## Manual Next Steps

```bash
cd ~/AgenticOS
agentos test
agentos bug-hunt
```

Then open the newest reports in Obsidian.
"""

    plan_path = PATCH_DIR / f"{STAMP} Patch Plan.md"
    latest_plan = PATCH_DIR / "latest Patch Plan.md"
    cycle_path = FIX_DIR / f"{STAMP} Fix Cycle.md"

    cycle_lines = [
        "---",
        "tags: [agentic-os, iterative-fixes, cycle]",
        f"created: {datetime.now().isoformat(timespec='seconds')}",
        "---",
        "",
        f"# AgenticOS Fix Cycle - {STAMP}",
        "",
        "## Timeline",
        "",
        *[f"- {item}" for item in timeline],
        "",
        "## Run Folder",
        "",
        f"`{RUN_DIR}`",
        "",
        "## Patch Plan",
        "",
        f"See: `{plan_path}`",
        "",
        "## Safety Note",
        "",
        "No patches were applied automatically. Review the patch plan manually.",
        "",
    ]

    for p in [plan_path, latest_plan]:
        p.write_text(plan + "\n", encoding="utf-8")
    cycle_path.write_text("\n".join(cycle_lines), encoding="utf-8")
    (RUN_DIR / "03-patch-plan.md").write_text(plan + "\n", encoding="utf-8")
    print(f"Wrote fix cycle: {cycle_path}")
    print(f"Wrote patch plan: {plan_path}")

if __name__ == "__main__":
    main()
