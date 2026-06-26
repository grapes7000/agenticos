#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, date
from pathlib import Path
import argparse
import os
import shlex
import subprocess
import textwrap

HOME = Path.home()
ROOT = Path(os.getenv("AGENTOS_HOME", str(HOME / "AgenticOS"))).expanduser()
VAULT = Path(os.getenv("OBSIDIAN_VAULT", str(HOME / "vault"))).expanduser()
TODAY = date.today().isoformat()
STAMP = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
OUT_DIR = VAULT / "Agentic OS" / "Security Reports"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def run(cmd: str, timeout: int = 60) -> tuple[int, str]:
    try:
        result = subprocess.run(
            cmd,
            cwd=str(ROOT) if ROOT.exists() else str(HOME),
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        output = (result.stdout or "") + (("\nSTDERR:\n" + result.stderr) if result.stderr else "")
        return result.returncode, output.strip()
    except subprocess.TimeoutExpired:
        return 124, f"Command timed out after {timeout}s: {cmd}"
    except Exception as e:
        return 999, f"Command failed: {cmd}\n{e}"


def has_cmd(name: str) -> bool:
    rc, _ = run(f"command -v {shlex.quote(name)}", timeout=10)
    return rc == 0


def section(title: str, body: str) -> str:
    return f"\n## {title}\n\n{body.strip() if body.strip() else '_No output._'}\n"


def code_block(text: str, lang: str = "text") -> str:
    if not text.strip():
        text = "No output."
    return f"```{lang}\n{text[:20000]}\n```"


def command_section(title: str, cmd: str, timeout: int = 60) -> str:
    rc, out = run(cmd, timeout=timeout)
    body = f"Command: `{cmd}`\n\nReturn code: `{rc}`\n\n" + code_block(out)
    return section(title, body)


def optional_tool_section(title: str, binary: str, cmd: str, timeout: int = 120) -> str:
    if not has_cmd(binary):
        return section(title, f"`{binary}` is not installed. Optional install: `sudo apt install {binary}`")
    return command_section(title, cmd, timeout=timeout)


def summarize_ports() -> str:
    rc, out = run("ss -tulpn", timeout=30)
    risky = []
    for line in out.splitlines():
        if "0.0.0.0:" in line or "[::]:" in line:
            risky.append(line)
    body = f"Command: `ss -tulpn`\n\nReturn code: `{rc}`\n\n"
    if risky:
        body += "### LAN/Wide-bind listeners spotted\n\nThese lines may be reachable beyond localhost. Review them carefully.\n\n"
        body += code_block("\n".join(risky)) + "\n\n"
    body += "### Full port listing\n\n" + code_block(out)
    return section("Open Ports", body)


def docker_section() -> str:
    if not has_cmd("docker"):
        return section("Docker", "Docker command not found.")
    rc, out = run('docker ps --format "table {{.Names}}\\t{{.Image}}\\t{{.Ports}}"', timeout=30)
    wide = []
    for line in out.splitlines():
        if "0.0.0.0:" in line or ":::" in line:
            wide.append(line)
    body = f"Command: `docker ps --format ...`\n\nReturn code: `{rc}`\n\n"
    if wide:
        body += "### Containers with wide-bind ports\n\n"
        body += code_block("\n".join(wide)) + "\n\n"
    body += "### All running containers\n\n" + code_block(out)
    return section("Docker Containers + Ports", body)


def openclaw_section() -> str:
    if not has_cmd("openclaw"):
        return section("OpenClaw", "OpenClaw command not found.")
    parts = []
    for title, cmd in [
        ("gateway status", "openclaw gateway status"),
        ("commands.bash", "openclaw config get commands.bash"),
        ("commands.text", "openclaw config get commands.text"),
        ("elevated enabled", "openclaw config get tools.elevated.enabled"),
        ("webchat allowFrom", "openclaw config get tools.elevated.allowFrom.webchat"),
        ("exec policy", "openclaw exec-policy show"),
    ]:
        rc, out = run(cmd, timeout=60)
        parts.append(f"### {title}\n\nCommand: `{cmd}`\nReturn code: `{rc}`\n\n{code_block(out)}")
    return section("OpenClaw Safety State", "\n\n".join(parts))


def hermes_section() -> str:
    if not has_cmd("hermes"):
        return section("Hermes", "Hermes command not found.")
    parts = []
    for title, cmd in [
        ("cron list", "hermes cron list"),
        ("gateway status", "hermes gateway status"),
    ]:
        rc, out = run(cmd, timeout=60)
        parts.append(f"### {title}\n\nCommand: `{cmd}`\nReturn code: `{rc}`\n\n{code_block(out)}")
    return section("Hermes State", "\n\n".join(parts))


def searxng_section() -> str:
    url = os.getenv("SEARXNG_BASE_URL", "http://localhost:8888")
    cmd = f'curl -s -I {shlex.quote(url)} | head -n 20 && echo && curl -s {shlex.quote(url + "/search?q=agenticos&format=json")} | head -c 500'
    return command_section("SearXNG Check", cmd, timeout=30)


def main() -> None:
    parser = argparse.ArgumentParser(description="AgenticOS security + system health audit")
    parser.add_argument("--deep", action="store_true", help="Run slower optional rootkit/package tools when available")
    args = parser.parse_args()

    lines: list[str] = []
    lines.extend([
        "---",
        "tags: [agentic-os, security, audit]",
        f"created: {TODAY}",
        f"run_id: {STAMP}",
        "---",
        "",
        f"# Security + Health Audit - {STAMP}",
        "",
        "This report collects facts for review. It does not apply fixes.",
        "",
        "## Safety Notes",
        "",
        "- Review wide-bind ports such as `0.0.0.0` carefully.",
        "- Review OpenClaw exec/elevated settings carefully.",
        "- Do not paste secrets/private keys/API keys into external models.",
        "- Scanner warnings can be false positives; investigate before panicking.",
    ])

    lines.append(command_section("System Basics", "hostnamectl 2>/dev/null || hostname; uname -a; uptime; free -h; df -h", timeout=30))
    lines.append(command_section("Failed System Services", "systemctl --failed", timeout=30))
    lines.append(command_section("Failed User Services", "systemctl --user --failed", timeout=30))
    lines.append(summarize_ports())
    lines.append(command_section("Firewall", "sudo -n ufw status verbose 2>/dev/null || ufw status verbose 2>/dev/null || echo 'ufw unavailable or sudo required'", timeout=30))
    lines.append(docker_section())
    lines.append(command_section("Autostart + User Units", "echo 'User unit files:'; systemctl --user list-unit-files | grep -Ei 'openclaw|hermes|ollama|agent|qwen|homepage|docker' || true; echo; echo 'Autostart folder:'; ls -lah ~/.config/autostart 2>/dev/null || true; echo; echo 'Crontab:'; crontab -l 2>/dev/null || true", timeout=45))
    lines.append(command_section("Recent Serious Logs", "journalctl -p 3 -xb --no-pager | tail -n 120", timeout=45))
    lines.append(openclaw_section())
    lines.append(hermes_section())
    lines.append(command_section("Ollama", "ollama list 2>/dev/null || echo 'ollama not available'; curl -s http://localhost:11434/api/tags 2>/dev/null | head -c 1000 || true", timeout=30))
    lines.append(searxng_section())
    lines.append(optional_tool_section("Lynis Quick Audit", "lynis", "sudo -n lynis audit system --quick --no-colors 2>/dev/null || lynis audit system --quick --no-colors", timeout=180))
    lines.append(optional_tool_section("Debsums Package Integrity", "debsums", "debsums -s", timeout=180))

    if args.deep:
        lines.append(optional_tool_section("rkhunter", "rkhunter", "sudo -n rkhunter --check --sk 2>/dev/null || rkhunter --check --sk", timeout=600))
        lines.append(optional_tool_section("chkrootkit", "chkrootkit", "sudo -n chkrootkit 2>/dev/null || chkrootkit", timeout=600))
    else:
        lines.append(section("Deep Scanners Skipped", "Run `agentos security --deep` later to include `rkhunter` and `chkrootkit` if installed."))

    out = OUT_DIR / f"{STAMP} Security Audit.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote security audit: {out}")


if __name__ == "__main__":
    main()
