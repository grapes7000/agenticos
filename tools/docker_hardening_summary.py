#!/usr/bin/env python3
"""Create a plain-English Docker hardening summary using local Ollama if available."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


def run(cmd, input_text: Optional[str] = None, timeout: int = 180) -> Tuple[int, str]:
    try:
        p = subprocess.run(cmd, input=input_text, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, timeout=timeout)
        return p.returncode, p.stdout.strip()
    except FileNotFoundError:
        return 127, f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "Timed out waiting for local model summary"
    except Exception as e:
        return 1, str(e)


def latest_file(folder: Path, pattern: str) -> Optional[Path]:
    files = sorted(folder.glob(pattern), key=lambda p: p.stat().st_mtime if p.exists() else 0)
    return files[-1] if files else None


def fallback_summary(text: str) -> str:
    lines = text.splitlines()
    exposed = [l for l in lines if "LAN_EXPOSED" in l]
    private = [l for l in exposed if "probably private" in l]
    warnings = [l for l in lines if "warning" in l.lower() or "failed" in l.lower()]
    out = []
    out.append("# Docker Hardening Plain-English Summary")
    out.append("")
    out.append("Local AI summary was not available, so this fallback summary used simple rule-based checks.")
    out.append("")
    out.append("## What looks healthy")
    out.append("- The audit completed and wrote a Docker hardening report, services map, and patch plan.")
    out.append("- No changes were applied automatically.")
    out.append("")
    out.append("## What looks risky")
    if private:
        out.append(f"- Found {len(private)} likely-private LAN-exposed port entries. These should be reviewed first.")
    elif exposed:
        out.append(f"- Found {len(exposed)} LAN-exposed port entries. Review which ones really need LAN access.")
    else:
        out.append("- No LAN-exposed compose ports were detected by the parser.")
    if warnings:
        out.append(f"- Found {len(warnings)} warning/failure-looking lines. Check the full report.")
    out.append("")
    out.append("## Best next action")
    out.append("- Open the patch plan, choose one stack, back up its compose file, change one private port to 127.0.0.1, validate with docker compose config, restart only that stack, then verify it still works.")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=os.environ.get("OBSIDIAN_VAULT", "~/vault"))
    ap.add_argument("--model", default=os.environ.get("AGENTOS_DOCKER_SUMMARY_MODEL", "qwen2.5-coder:7b"))
    args = ap.parse_args()

    base = Path(args.vault).expanduser() / "Agentic OS"
    report_dir = base / "Docker Hardening Reports"
    plan_dir = base / "Patch Plans"
    summary_dir = base / "Docker Hardening Summaries"
    summary_dir.mkdir(parents=True, exist_ok=True)

    report = latest_file(report_dir, "*Docker Hardening Audit.md")
    plan = latest_file(plan_dir, "*Docker Hardening Patch Plan.md")
    service_map = base / "Self-Hosted Services Map.md"

    if not report:
        print("No Docker hardening audit report found. Run agentos-docker-hardening first.")
        return 1

    parts = ["# AUDIT REPORT\n", report.read_text(errors="replace")[:18000]]
    if plan and plan.exists():
        parts += ["\n\n# PATCH PLAN\n", plan.read_text(errors="replace")[:12000]]
    if service_map.exists():
        parts += ["\n\n# SERVICES MAP\n", service_map.read_text(errors="replace")[:12000]]
    source = "".join(parts)

    prompt = f"""You are reviewing a local Linux Mint self-hosted Docker setup.
Use ONLY the audit text below. Do not invent findings. Do not suggest applying risky fixes automatically.
Write a plain-English summary for a beginner.

Include these sections:
1. Overall security posture
2. What looks healthy
3. What looks risky
4. Which services/ports need review first
5. Build quality / compose quality concerns
6. Top 5 safest next steps
7. What not to touch yet

AUDIT TEXT:
{source}
"""

    rc, out = run(["ollama", "run", args.model], input_text=prompt, timeout=240)
    if rc != 0 or not out.strip():
        out = fallback_summary(source)
        ai_note = f"Local Ollama summary failed or was unavailable: {out[:200]}"
    else:
        ai_note = f"Generated with local Ollama model `{args.model}`."

    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_path = summary_dir / f"{stamp} Docker Hardening Summary.md"
    text = f"# Docker Hardening Summary - {datetime.now().strftime('%Y-%m-%d')}\n\n{ai_note}\n\n{out.strip()}\n"
    out_path.write_text(text, encoding="utf-8")
    print(f"Wrote summary: {out_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
