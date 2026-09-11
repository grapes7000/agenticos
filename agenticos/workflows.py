from __future__ import annotations

from dataclasses import asdict, dataclass
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import urllib.request

from .settings import Settings


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class StatusReport:
    headline: str
    checks: tuple[Check, ...]
    suggestions: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _disk_check(path: Path) -> Check:
    usage = shutil.disk_usage(path)
    percent = round((usage.used / usage.total) * 100)
    free_gib = usage.free / (1024**3)
    state = "critical" if percent >= 95 else "warning" if percent >= 85 else "ok"
    return Check("Disk", state, f"{percent}% used; {free_gib:.1f} GiB available")


def _ollama_check(settings: Settings) -> Check:
    try:
        with urllib.request.urlopen(f"{settings.ollama_url}/api/tags", timeout=2) as response:
            ok = response.status == 200
        return Check("Ollama", "ok" if ok else "warning", settings.ollama_url)
    except Exception as error:
        return Check("Ollama", "offline", f"{settings.ollama_url}: {type(error).__name__}")


def _database_check(settings: Settings) -> Check:
    if not settings.database_path.exists():
        legacy = settings.root / "data" / "db" / "agent_os.sqlite"
        detail = f"legacy database ready to migrate: {legacy}" if legacy.exists() else "not initialized"
        return Check("Database", "warning", detail)
    try:
        with sqlite3.connect(settings.database_path) as connection:
            result = connection.execute("PRAGMA quick_check").fetchone()[0]
        return Check("Database", "ok" if result == "ok" else "critical", str(settings.database_path))
    except sqlite3.Error as error:
        return Check("Database", "critical", str(error))


def _git_check(settings: Settings) -> Check:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=settings.root,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    if result.returncode != 0:
        return Check("Git", "warning", result.stderr.strip() or "status unavailable")
    count = len([line for line in result.stdout.splitlines() if line.strip()])
    return Check("Git", "warning" if count else "ok", f"{count} uncommitted paths")


def collect_status(settings: Settings) -> StatusReport:
    checks = (
        _disk_check(settings.root),
        _database_check(settings),
        _ollama_check(settings),
        _git_check(settings),
        Check("Vault", "ok" if settings.vault.is_dir() else "warning", str(settings.vault)),
        Check(
            "ChatGPT memory",
            "ok" if settings.memory_database.is_file() else "warning",
            str(settings.memory_database),
        ),
    )
    problems = [check for check in checks if check.status != "ok"]
    headline = "AgenticOS is healthy." if not problems else f"AgenticOS has {len(problems)} item(s) to review."
    suggestions: list[str] = []
    if any(check.name == "Disk" and check.status in {"critical", "warning"} for check in checks):
        suggestions.append("Reclaim disk space before running large local models or memory extraction.")
    if any(check.name == "Git" and check.status == "warning" for check in checks):
        suggestions.append("Review and checkpoint the current AgenticOS source changes.")
    if any(check.name == "Ollama" and check.status == "offline" for check in checks):
        suggestions.append("Start Ollama only when an AI-assisted workflow is needed.")
    return StatusReport(headline, checks, tuple(suggestions))


def maintenance_suggestions(settings: Settings) -> tuple[str, ...]:
    report = collect_status(settings)
    suggestions = list(report.suggestions)
    legacy_db = settings.root / "data" / "db" / "agent_os.sqlite"
    if legacy_db.exists() and not settings.database_path.exists():
        suggestions.append("Migrate the legacy AgenticOS database to the configured data directory.")
    old_wrappers = list((settings.root / "bin").glob("*.backup*")) + list(
        (settings.root / "bin").glob("*.before-*")
    )
    if old_wrappers:
        suggestions.append(f"Archive {len(old_wrappers)} obsolete CLI wrapper backup(s) after reviewing Git history.")
    if not suggestions:
        suggestions.append("No immediate maintenance action is recommended.")
    return tuple(suggestions)


def doctor_checks(settings: Settings) -> tuple[Check, ...]:
    checks = list(collect_status(settings).checks)
    checks.extend(
        Check(command, "ok" if shutil.which(command) else "optional", shutil.which(command) or "not installed")
        for command in ("python3", "ollama", "hermes", "openclaw")
    )
    checks.append(Check("Host", "ok", socket.gethostname()))
    checks.append(Check("Dry run", "ok" if settings.dry_run else "warning", str(settings.dry_run).lower()))
    return tuple(checks)
