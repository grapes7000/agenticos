#!/usr/bin/env python3
"""Create a read-only AgenticOS homecoming briefing.

This agent is intentionally non-destructive: it observes system state, summarizes
what changed, and writes Markdown notes into Obsidian. It never moves/deletes
files, edits Docker/SSH/system config, or runs privileged commands.
"""
from __future__ import annotations

import datetime as dt
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Iterable

HOME = Path.home()
ROOT = Path(os.getenv("AGENTOS_HOME", HOME / "AgenticOS")).expanduser()
DB = ROOT / "data/db/agent_os.sqlite"


def choose_vault() -> Path:
    candidates = []
    env = os.getenv("OBSIDIAN_VAULT") or os.getenv("AGENTOS_VAULT")
    if env:
        candidates.append(Path(env).expanduser())
    candidates.extend([
        HOME / "Documents" / "Obsidian Vault",
        HOME / "vault",
    ])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


VAULT = choose_vault()
TODAY = dt.date.today().isoformat()
STAMP = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def run(cmd: list[str], timeout: int = 20) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT) if ROOT.exists() else None,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        text = out if out else err
        if out and err:
            text = out + "\n\nSTDERR:\n" + err
        return proc.returncode, text[:9000]
    except Exception as exc:
        return 1, f"{type(exc).__name__}: {exc}"


def shell(cmd: str, timeout: int = 20) -> tuple[int, str]:
    return run(["bash", "-lc", cmd], timeout=timeout)


def fenced(text: str, lang: str = "text") -> list[str]:
    return [f"```{lang}", text.strip() or "(no output)", "```"]


def latest_notes(rel: str, limit: int = 5) -> list[Path]:
    folder = VAULT / "Agentic OS" / rel
    if not folder.exists():
        return []
    return sorted(folder.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]


def db_counts() -> list[str]:
    if not DB.exists():
        return [f"- Database missing: `{DB}`"]
    lines = []
    try:
        with sqlite3.connect(DB) as con:
            for table in ["files", "actions", "lessons", "runs", "research_sources", "memory_chunks", "handoffs", "evaluations", "agent_runs"]:
                try:
                    count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    lines.append(f"- `{table}`: **{count}** rows")
                except Exception:
                    pass
            try:
                sensitive = con.execute("SELECT COUNT(*) FROM files WHERE sensitive = 1").fetchone()[0]
                lines.append(f"- Sensitive-looking indexed files: **{sensitive}**")
            except Exception:
                pass
    except Exception as exc:
        lines.append(f"- DB check failed: `{exc}`")
    return lines or ["- Database exists, but no known tables were readable."]


def collect() -> dict[str, tuple[int, str]]:
    commands = {
        "System snapshot": "date; uptime; uname -a; printf '\\nUser: '; whoami; printf '\\nHost: '; hostname",
        "Disk and memory": "df -hT --exclude-type=tmpfs --exclude-type=devtmpfs; printf '\\n'; free -h",
        "Home folder pressure": "du -h --max-depth=1 \"$HOME\" 2>/dev/null | sort -h | tail -25",
        "Failed systemd units": "systemctl --failed --no-pager 2>/dev/null || true; printf '\\n-- user --\\n'; systemctl --user --failed --no-pager 2>/dev/null || true",
        "Listening ports": "ss -tulpen 2>/dev/null | sed -n '1,120p' || true",
        "Docker containers": "docker ps --format 'table {{.Names}}\\t{{.Image}}\\t{{.Status}}\\t{{.Ports}}' 2>/dev/null || echo 'Docker unavailable or permission denied'",
        "Docker disk": "docker system df 2>/dev/null || echo 'Docker unavailable or permission denied'",
        "APT update state": "apt list --upgradable 2>/dev/null | sed -n '1,80p'",
        "Hermes cron": "command -v hermes >/dev/null && hermes cron list 2>&1 | sed -n '1,160p' || echo 'hermes not found'",
        "Local AI": "command -v ollama >/dev/null && ollama list 2>&1 | sed -n '1,80p' || echo 'ollama not found'",
    }
    return {name: shell(cmd, timeout=25) for name, cmd in commands.items()}


def risk_notes(collected: dict[str, tuple[int, str]]) -> list[str]:
    ports = collected.get("Listening ports", (0, ""))[1]
    docker = collected.get("Docker containers", (0, ""))[1]
    apt = collected.get("APT update state", (0, ""))[1]
    failed = collected.get("Failed systemd units", (0, ""))[1]

    notes = []
    if "0.0.0.0:" in ports or "*:" in ports:
        notes.append("- **Network exposure:** services are listening beyond localhost. Review Docker-published ports before exposing anything to the internet.")
    if any(port in docker for port in ["5678", "9000", "9443", "2283", "5006", "3010"]):
        notes.append("- **Self-hosted app surface:** n8n/Portainer/Immich/Actual/Linkwarden-style ports appear active. Keep them behind VPN/Tailscale or bind to `127.0.0.1`.")
    if "Listing..." in apt and len([ln for ln in apt.splitlines() if "/" in ln]) > 0:
        notes.append("- **Updates:** APT reports pending upgrades. Review/install when you are back.")
    elif "Listing..." in apt:
        notes.append("- **Updates:** no obvious APT upgrades listed.")
    if "0 loaded units listed" not in failed and "UNIT" in failed:
        notes.append("- **Services:** at least one failed systemd unit may need review.")
    if not notes:
        notes.append("- No urgent red flags detected by the lightweight homecoming scan.")
    return notes


def note_links() -> list[str]:
    sections = [
        "Daily Briefings",
        "File Plans",
        "Health",
        "Operator Reports",
        "Memory Digests",
        "Change Reports",
        "Evaluations",
        "Handoffs",
        "Security Reports",
    ]
    lines: list[str] = []
    for section in sections:
        notes = latest_notes(section, limit=3)
        lines.append(f"### {section}")
        if not notes:
            lines.append("- No notes found yet.")
        else:
            for p in notes:
                lines.append(f"- [[{p.stem}]] — `{p}`")
        lines.append("")
    return lines


def write_approval_queue() -> Path:
    out_dir = VAULT / "Agentic OS" / "Command Queue"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{TODAY} Approval Queue.md"
    content = f"""---
tags: [agentic-os, command-queue, approval-required]
created: {dt.datetime.now().isoformat(timespec='seconds')}
---

# Approval Queue - {TODAY}

These are **suggested actions only**. AgenticOS should not run them without your approval.

## High-impact security actions

- [ ] Review Docker Compose files and change private app ports from `0.0.0.0` to `127.0.0.1` where LAN access is not needed.
- [ ] Decide whether Postfix/mail port `25` is needed. If not: `sudo systemctl disable --now postfix`.
- [ ] Verify SSH key login works, then explicitly disable SSH password login.
- [ ] Confirm Timeshift snapshots and personal-file backups are actually running.

## Organization actions

- [ ] Empty Trash after manual review.
- [ ] Review duplicate Linux Mint ISO files and delete only confirmed duplicates.
- [ ] Inspect accidental comma/brace folders before deleting them.
- [ ] Review today's File Butler dry-run note; no files should be moved automatically.

## Autonomy rule

AgenticOS can observe, summarize, and draft plans by itself. It needs your approval before privileged changes, deletes, moves, config rewrites, or external publishing.
"""
    out.write_text(content, encoding="utf-8")
    return out


def write_homecoming(collected: dict[str, tuple[int, str]], approval_note: Path) -> Path:
    out_dir = VAULT / "Agentic OS" / "Homecoming"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{STAMP} Homecoming Briefing.md"
    lines: list[str] = [
        "---",
        "tags: [agentic-os, homecoming, autonomy, system-report]",
        f"created: {dt.datetime.now().isoformat(timespec='seconds')}",
        "---",
        "",
        f"# Homecoming Briefing - {STAMP}",
        "",
        "## What this is",
        "",
        "A read-only AgenticOS check-in generated while you were away. It summarizes system health, self-hosted services, file organization signals, and next actions that need approval.",
        "",
        "## Executive summary",
        "",
        *risk_notes(collected),
        "",
        "## Autonomy status",
        "",
        f"- AgenticOS root: `{ROOT}`",
        f"- Obsidian vault: `{VAULT}`",
        f"- Database: `{DB}`",
        f"- Approval queue: [[{approval_note.stem}]]",
        "- Mode: **read-only / dry-run**. No files were moved, deleted, or edited outside AgenticOS report files.",
        "",
        "## AgenticOS memory/database counts",
        "",
        *db_counts(),
        "",
        "## Fresh notes to review",
        "",
        *note_links(),
        "## System evidence",
        "",
    ]
    for name, (code, text) in collected.items():
        lines.extend([f"### {name}", "", f"Exit code: `{code}`", "", *fenced(text), ""])
    lines.extend([
        "## Recommended next step",
        "",
        "The next real AgenticOS milestone is an **approval-gated operator loop**:",
        "",
        "1. Observe continuously: system health, Docker exposure, Downloads/Desktop/Documents drift, cron status, Ollama/Hermes status.",
        "2. Write notes and command queues into Obsidian.",
        "3. Ask for approval before any destructive, privileged, or network-exposing action.",
        "4. After approval, apply one small fix and write a before/after note.",
        "",
        "This makes the computer feel autonomous without letting it silently break trust.",
    ])
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def update_current_pointer(homecoming_note: Path, approval_note: Path) -> Path:
    out = VAULT / "Agentic OS" / "AgenticOS Current Status.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    content = f"""---
tags: [agentic-os, status]
updated: {dt.datetime.now().isoformat(timespec='seconds')}
---

# AgenticOS Current Status

## Latest homecoming briefing

- [[{homecoming_note.stem}]]
- Path: `{homecoming_note}`

## Current approval queue

- [[{approval_note.stem}]]
- Path: `{approval_note}`

## How to refresh manually

```bash
agentos homecoming
```

## Safety mode

- Observations and Markdown reports: allowed.
- File moves/deletes, sudo changes, Docker/SSH config edits, and public exposure changes: approval required.
"""
    out.write_text(content, encoding="utf-8")
    return out


def main() -> int:
    VAULT.mkdir(parents=True, exist_ok=True)
    collected = collect()
    approval = write_approval_queue()
    homecoming = write_homecoming(collected, approval)
    current = update_current_pointer(homecoming, approval)
    print(f"Wrote homecoming briefing: {homecoming}")
    print(f"Wrote approval queue: {approval}")
    print(f"Updated current status: {current}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
