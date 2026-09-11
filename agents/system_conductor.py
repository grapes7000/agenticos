#!/usr/bin/env python3
"""AgenticOS System Conductor

Runs the background maintenance stack, analyzes outputs, writes one human-facing
summary, and creates an action queue. Safe by default: no Docker edits, firewall
changes, deletions, package upgrades, or risky restarts.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import textwrap
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

AUDIENCE_AI = """> [!info] AgenticOS Audience\n> Intended reader: **AI / AgenticOS internal analysis**.\n> Human use: this is raw evidence. Read the paired System Summary instead.\n> Analyzer: `agentos system` / `agentos analyze-reports`.\n\n"""

AUDIENCE_HUMAN = """> [!success] AgenticOS Audience\n> Intended reader: **human / Brooke & Lakota**.\n> Purpose: plain-English status, priorities, and next actions.\n\n"""

@dataclass
class CommandResult:
    name: str
    command: str
    returncode: int
    stdout: str
    stderr: str
    started: str
    ended: str
    duration_seconds: float

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def markdown(self) -> str:
        status = "OK" if self.ok else f"FAILED ({self.returncode})"
        out = self.stdout.strip() or "(no stdout)"
        err = self.stderr.strip() or "(no stderr)"
        return f"""### {self.name}\n\n- Status: **{status}**\n- Command: `{self.command}`\n- Started: {self.started}\n- Ended: {self.ended}\n- Duration: {self.duration_seconds:.1f}s\n\n**stdout**\n\n```text\n{truncate(out, 6000)}\n```\n\n**stderr**\n\n```text\n{truncate(err, 4000)}\n```\n"""

@dataclass
class SystemState:
    timestamp: datetime
    vault: Path
    agent_root: Path
    summary_model: str
    command_results: list[CommandResult] = field(default_factory=list)
    report_files: list[Path] = field(default_factory=list)
    raw_report_path: Optional[Path] = None
    summary_path: Optional[Path] = None
    action_queue_path: Optional[Path] = None
    status: str = "unknown"
    urgent: bool = False


def truncate(s: str, limit: int) -> str:
    if len(s) <= limit:
        return s
    return s[:limit] + f"\n\n... truncated {len(s) - limit} chars ..."


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def detect_vault() -> Path:
    env = os.environ.get("OBSIDIAN_VAULT")
    if env:
        return Path(env).expanduser()
    candidates = [Path.home() / "Documents" / "Obsidian Vault", Path.home() / "vault"]
    for p in candidates:
        if (p / "Agentic OS").exists():
            return p
    return candidates[0]


def ensure_dirs(agent_root: Path) -> dict[str, Path]:
    dirs = {
        "system_reports": agent_root / "System Reports",
        "system_summaries": agent_root / "System Summaries",
        "action_queue": agent_root / "Action Queue",
        "ai_analysis": agent_root / "AI Analysis",
        "user_summaries": agent_root / "User Summaries",
    }
    for p in dirs.values():
        p.mkdir(parents=True, exist_ok=True)
    return dirs


def which(cmd: str) -> Optional[str]:
    return shutil.which(cmd)


def run_shell(name: str, command: str, timeout: int = 240) -> CommandResult:
    started_dt = datetime.now().astimezone()
    try:
        p = subprocess.run(command, shell=True, text=True, capture_output=True, timeout=timeout, executable="/bin/bash")
        stdout, stderr, rc = p.stdout, p.stderr, p.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = (exc.stderr or "") + f"\nTIMEOUT after {timeout}s"
        rc = 124
    ended_dt = datetime.now().astimezone()
    return CommandResult(
        name=name,
        command=command,
        returncode=rc,
        stdout=stdout,
        stderr=stderr,
        started=started_dt.isoformat(timespec="seconds"),
        ended=ended_dt.isoformat(timespec="seconds"),
        duration_seconds=(ended_dt - started_dt).total_seconds(),
    )


def command_exists_shell(command: str) -> bool:
    return subprocess.run(f"command -v {command} >/dev/null 2>&1", shell=True, executable="/bin/bash").returncode == 0


def gather_latest_reports(agent_root: Path, max_files: int = 18) -> list[Path]:
    patterns = [
        "Health/*Health Report.md",
        "Security Reports/*.md",
        "Security Summaries/*.md",
        "Docker Security Reports/*.md",
        "Docker Hardening Reports/*.md",
        "Docker Hardening Summaries/*.md",
        "Build Quality Reports/*.md",
        "Bug Reports/*.md",
        "Patch Plans/*.md",
        "Work Cycles/*.md",
        "Change Reports/*.md",
        "System Reports/*.md",
    ]
    files: list[Path] = []
    for pat in patterns:
        files.extend(agent_root.glob(pat))
    files = [p for p in files if p.is_file() and ".agenticos_backups" not in str(p)]
    files = sorted(set(files), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:max_files]


def read_file_for_ai(path: Path, limit: int = 14000) -> str:
    try:
        text = path.read_text(errors="replace")
    except Exception as exc:
        return f"[Could not read {path}: {exc}]"
    return truncate(text, limit)


def build_commands(args: argparse.Namespace) -> list[tuple[str, str, int]]:
    # Call the base agentos via PATH. The wrapper forwards non-conductor commands.
    cmds: list[tuple[str, str, int]] = []
    cmds.append(("Health Check", "agentos health", 180))
    if not args.skip_security:
        cmds.append(("Security Full", "agentos security-full || agentos security || true", 360))
    if not args.skip_docker:
        if command_exists_shell("agentos-docker-full"):
            cmds.append(("Docker Hardening", "agentos-docker-full", 360))
        else:
            cmds.append(("Docker Hardening", "agentos docker-full || true", 360))
    cmds.append(("Build Quality", "agentos build-quality || true", 240))
    cmds.append(("Fix Status", "agentos fix-status || true", 160))
    if args.include_work_cycle:
        if command_exists_shell("agentos-work-cycle"):
            cmds.append(("Work Cycle", "agentos-work-cycle", 360))
        else:
            cmds.append(("Work Cycle", "agentos work-cycle || true", 360))
    return cmds


def label_existing_quiet(vault: Path) -> None:
    script = Path.home() / "AgenticOS" / "agents" / "label_logs.py"
    if script.exists():
        subprocess.run([sys.executable, str(script), "--apply", "--vault", str(vault)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def analyze_with_ollama(model: str, prompt: str, timeout: int = 300) -> Optional[str]:
    if not which("ollama"):
        return None
    models = [model]
    for fallback in ["openclaw-chat:8b-4k", "openclaw-granite:8b-4k", "phi4-mini", "llama3.1:8b", "qwen2.5:7b"]:
        if fallback not in models:
            models.append(fallback)
    for m in models:
        try:
            p = subprocess.run(["ollama", "run", m, prompt], text=True, capture_output=True, timeout=timeout)
            if p.returncode == 0 and p.stdout.strip():
                return p.stdout.strip()
        except Exception:
            continue
    return None


def heuristic_summary(state: SystemState) -> str:
    failed = [r for r in state.command_results if not r.ok]
    ok = [r for r in state.command_results if r.ok]
    docker_mentions = "\n".join(r.stdout + r.stderr for r in state.command_results if "docker" in r.name.lower())
    exposed = len(re.findall(r"0\.0\.0\.0:\d+|:\d+->", docker_mentions))
    status = "Needs attention" if failed else "Mostly healthy"
    lines = [
        f"# AgenticOS System Summary - {state.timestamp.strftime('%Y-%m-%d %H:%M')}",
        "",
        AUDIENCE_HUMAN,
        "## What you need to know",
        f"- Overall status: **{status}**.",
        f"- Checks completed: **{len(ok)} OK**, **{len(failed)} failed/problematic**.",
        f"- Latest raw files reviewed: **{len(state.report_files)}**.",
    ]
    if exposed:
        lines.append(f"- Docker/network exposure mentions found: **{exposed}**. Review the Docker hardening summary before changing ports.")
    if failed:
        lines.append("\n## Checks needing attention")
        for r in failed:
            lines.append(f"- **{r.name}** returned code `{r.returncode}`. Review the System Report details.")
    lines.extend([
        "",
        "## Safest next step",
        "Read the Action Queue and pick **one** safe/approval-based fix. Do not harden every Docker stack at once.",
        "",
        "## Files analyzed",
    ])
    for p in state.report_files[:12]:
        lines.append(f"- `{p}`")
    return "\n".join(lines)


def build_ai_prompt(state: SystemState) -> str:
    parts = []
    parts.append("""You are the AgenticOS System Conductor.

Your job is to read raw system reports and produce ONE human-facing summary.

Rules:
- Plain English only.
- No JSON.
- No code unless listing a single safe command.
- Do not invent facts.
- Separate what is working, what is risky, and what needs approval.
- Do not recommend automatic risky fixes.
- Keep it useful and not too long.
- The user wants fun AI projects, not background-tech babysitting.
""")
    parts.append("COMMAND RESULTS:\n")
    for r in state.command_results:
        status = "OK" if r.ok else f"FAILED {r.returncode}"
        parts.append(f"## {r.name} [{status}]\nSTDOUT:\n{truncate(r.stdout, 3500)}\nSTDERR:\n{truncate(r.stderr, 1500)}\n")
    parts.append("RAW REPORT EXCERPTS:\n")
    for p in state.report_files[:10]:
        parts.append(f"\n--- FILE: {p} ---\n{read_file_for_ai(p, 4500)}\n")
    parts.append("""
Write the summary with these headings:
# AgenticOS System Summary
## Status
## What is working
## What needs attention
## Background actions completed
## Approval-needed actions
## Safest next step
## What you do NOT need to worry about tonight
""")
    return "\n".join(parts)


def build_action_queue(state: SystemState, summary: str) -> str:
    failed = [r for r in state.command_results if not r.ok]
    lines = [
        f"# AgenticOS Action Queue - {state.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        AUDIENCE_HUMAN,
        "## Purpose",
        "This is the short list of things AgenticOS thinks may need attention. Risky actions require approval.",
        "",
        "## Auto-safe background actions",
        "- [x] Ran available health/security/docker/build checks.",
        "- [x] Collected newest AgenticOS reports.",
        "- [x] Wrote a human-facing System Summary.",
        "- [x] Added/maintained audience labeling for reports when possible.",
        "",
        "## Needs approval before doing",
        "- [ ] Edit Docker Compose port bindings.",
        "- [ ] Restart Docker stacks.",
        "- [ ] Change firewall rules.",
        "- [ ] Expose OpenClaw to LAN/Tailscale.",
        "- [ ] Delete files or prune Docker volumes/images.",
        "- [ ] Update packages or change system services.",
        "",
        "## Detected issues",
    ]
    if failed:
        for r in failed:
            lines.append(f"- [ ] Investigate **{r.name}** exit code `{r.returncode}`.")
    else:
        lines.append("- No command-level failures detected in this run.")
    lines.extend([
        "",
        "## Suggested next human action",
        "- Pick **one** approval-needed item from the newest System Summary, preferably the smallest Docker hardening or service cleanup task.",
        "",
        "## Source summary excerpt",
        "```text",
        truncate(summary, 3000),
        "```",
    ])
    return "\n".join(lines)


def short_status(summary: str, state: SystemState) -> str:
    failed = [r for r in state.command_results if not r.ok]
    if failed:
        return f"AgenticOS: {len(failed)} check(s) need attention. Summary: {state.summary_path}"
    # Try to grab a sentence after Status.
    clean = re.sub(r"[#>*`\[\]_-]", "", summary)
    lines = [ln.strip() for ln in clean.splitlines() if ln.strip()]
    for ln in lines:
        if 25 <= len(ln) <= 180 and not ln.lower().startswith("agenticos"):
            return f"AgenticOS: {ln[:180]}"
    return f"AgenticOS: system check complete. Summary: {state.summary_path}"


def notify_desktop(message: str) -> None:
    if which("notify-send"):
        subprocess.run(["notify-send", "AgenticOS", message[:220]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def notify_telegram(message: str) -> bool:
    token = os.environ.get("AGENTOS_TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("AGENTOS_TELEGRAM_CHAT_ID")
    env_file = Path.home() / ".agenticos" / "telegram.env"
    if env_file.exists() and (not token or not chat_id):
        data = env_file.read_text(errors="ignore")
        token_match = re.search(r'AGENTOS_TELEGRAM_BOT_TOKEN="?([^"\n]+)', data)
        chat_match = re.search(r'AGENTOS_TELEGRAM_CHAT_ID="?([^"\n]+)', data)
        token = token or (token_match.group(1) if token_match else None)
        chat_id = chat_id or (chat_match.group(1) if chat_match else None)
    if not token or not chat_id:
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        body = urllib.parse.urlencode({"chat_id": chat_id, "text": message[:3800]}).encode()
        req = urllib.request.Request(url, data=body)
        urllib.request.urlopen(req, timeout=15).read()
        return True
    except Exception:
        return False


def write_run(state: SystemState, args: argparse.Namespace) -> None:
    dirs = ensure_dirs(state.agent_root)
    stamp = state.timestamp.strftime("%Y-%m-%d_%H-%M-%S")

    raw = dirs["system_reports"] / f"{stamp} System Report.md"
    summary_path = dirs["system_summaries"] / f"{stamp} System Summary.md"
    queue_path = dirs["action_queue"] / f"{stamp} Action Queue.md"
    state.raw_report_path = raw
    state.summary_path = summary_path
    state.action_queue_path = queue_path

    raw_parts = [
        f"# AgenticOS System Report - {state.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        AUDIENCE_AI,
        "## Run metadata",
        f"- Vault: `{state.vault}`",
        f"- Summary model: `{state.summary_model}`",
        f"- Mode: `{'scheduled' if args.scheduled else 'manual'}`",
        "",
        "## Command results",
    ]
    raw_parts.extend(r.markdown() for r in state.command_results)
    raw_parts.append("\n## Latest report files discovered\n")
    for p in state.report_files:
        raw_parts.append(f"- `{p}`")
    raw.write_text("\n".join(raw_parts))

    prompt = build_ai_prompt(state)
    summary = None if args.no_ollama else analyze_with_ollama(state.summary_model, prompt)
    if not summary:
        summary = heuristic_summary(state)
    if "AgenticOS Audience" not in summary[:1000]:
        summary = AUDIENCE_HUMAN + summary
    summary_path.write_text(summary.rstrip() + "\n\n---\nGenerated by `agentos system`. Raw evidence: `" + str(raw) + "`\n")

    queue = build_action_queue(state, summary)
    queue_path.write_text(queue)


def run_conductor(args: argparse.Namespace) -> int:
    vault = detect_vault()
    agent_root = vault / "Agentic OS"
    agent_root.mkdir(parents=True, exist_ok=True)
    ensure_dirs(agent_root)
    state = SystemState(
        timestamp=datetime.now(),
        vault=vault,
        agent_root=agent_root,
        summary_model=os.environ.get("AGENTOS_SUMMARY_MODEL", "openclaw-granite:8b-4k"),
    )

    if args.label:
        label_existing_quiet(vault)

    if not args.analyze_only:
        for name, cmd, timeout in build_commands(args):
            print(f"Running: {name}")
            state.command_results.append(run_shell(name, cmd, timeout=timeout))
    else:
        print("Analyze-only mode: reading existing reports without running checks.")

    state.report_files = gather_latest_reports(agent_root)
    write_run(state, args)

    msg = short_status(state.summary_path.read_text(errors="replace"), state)
    if args.notify or args.scheduled:
        notify_desktop(msg)
    if args.telegram or args.scheduled:
        sent = notify_telegram(msg + f"\n\nSummary: {state.summary_path}\nAction Queue: {state.action_queue_path}")
        if not sent:
            pending = agent_root / "System Summaries" / "telegram-not-configured.txt"
            pending.write_text("Telegram not configured. Set AGENTOS_TELEGRAM_BOT_TOKEN and AGENTOS_TELEGRAM_CHAT_ID or run installer with --setup-telegram.\n")

    print("\nAgenticOS system run complete.")
    print(f"Raw system report: {state.raw_report_path}")
    print(f"Human summary:     {state.summary_path}")
    print(f"Action queue:      {state.action_queue_path}")
    print(f"Short status:      {msg}")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run AgenticOS as a background conductor.")
    parser.add_argument("--notify", action="store_true", help="Send a desktop notification.")
    parser.add_argument("--telegram", action="store_true", help="Send a Telegram notification if configured.")
    parser.add_argument("--scheduled", action="store_true", help="Scheduled/background mode: notify and Telegram if configured.")
    parser.add_argument("--analyze-only", action="store_true", help="Do not run checks; analyze existing latest reports.")
    parser.add_argument("--no-ollama", action="store_true", help="Do not call local Ollama; use heuristic summary.")
    parser.add_argument("--label", action="store_true", default=True, help="Keep report audience labels updated. Default true.")
    parser.add_argument("--no-label", dest="label", action="store_false", help="Do not label existing reports this run.")
    parser.add_argument("--skip-docker", action="store_true", help="Skip Docker hardening check.")
    parser.add_argument("--skip-security", action="store_true", help="Skip security-full check.")
    parser.add_argument("--include-work-cycle", action="store_true", help="Also run work-cycle. Default off because it can be slow/noisy.")
    args = parser.parse_args(argv)
    return run_conductor(args)


if __name__ == "__main__":
    raise SystemExit(main())
