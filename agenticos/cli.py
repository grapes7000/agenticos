from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from typing import Iterable

from . import __version__
from .dashboard import render_dashboard
from .database import migrate_legacy_database
from .memory import errors as memory_errors
from .memory import list_projects, search as memory_search
from .settings import Settings, load_settings
from .workflows import Check, collect_status, doctor_checks, maintenance_suggestions


def _print_checks(checks: Iterable[Check]) -> None:
    symbols = {"ok": "OK", "warning": "WARN", "critical": "FAIL", "offline": "OFF", "optional": "OPT"}
    for check in checks:
        print(f"[{symbols.get(check.status, check.status.upper())}] {check.name}: {check.detail}")


def _legacy(settings: Settings, command: str, arguments: list[str]) -> int:
    routes = {
        "morning": settings.root / "scripts" / "morning_run.sh",
        "layer3": settings.root / "scripts" / "layer3_run.sh",
        "health": settings.root / "agents" / "health_watchdog.py",
        "security": settings.root / "agents" / "security_audit.py",
        "security-summary": settings.root / "agents" / "security_summary.py",
        "openclaw-prep": settings.root / "scripts" / "openclaw_prepare.sh",
        "bug-hunt": settings.root / "agents" / "bug_hunter.py",
        "fix-status": settings.root / "agents" / "fix_status.py",
    }
    target = routes.get(command)
    if target is None or not target.exists():
        print(f"Unknown legacy command: {command}", file=sys.stderr)
        return 2
    executable = [sys.executable, str(target)] if target.suffix == ".py" else [str(target)]
    environment = os.environ.copy()
    environment.update(
        {
            "AGENTOS_HOME": str(settings.root),
            "AGENTOS_VAULT": str(settings.vault),
            "OBSIDIAN_VAULT": str(settings.vault),
            "AGENTOS_MODEL": settings.model,
            "OLLAMA_HOST": settings.ollama_url,
        }
    )
    return subprocess.run(executable + arguments, env=environment, check=False).returncode


def _memory_command(settings: Settings, args: argparse.Namespace) -> int:
    try:
        if args.memory_command == "projects":
            rows = list_projects(settings)
        elif args.memory_command == "errors":
            rows = memory_errors(settings, project=args.project, limit=args.limit)
        elif args.memory_command == "search":
            rows = memory_search(
                settings, args.query, project=args.project, category=args.category, limit=args.limit
            )
        elif args.memory_command == "reindex":
            script = settings.root / "chatgpt-memory" / "src" / "knowledge_index.py"
            return subprocess.run(
                [sys.executable, str(script), "build", "--db", str(settings.memory_database), "--output", str(settings.memory_output_dir)],
                check=False,
            ).returncode
        else:
            raise ValueError("memory subcommand required")
    except (FileNotFoundError, sqlite3.Error, ValueError) as error:
        print(f"Memory error: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(rows, indent=2, default=str))
    else:
        for row in rows:
            if args.memory_command == "projects":
                print(f"{row['name']} — {row['conversations']} conversations, {row['knowledge_items']} items")
            else:
                print(f"[{row['project_slug']}/{row['category']}] {row['statement']}")
                print(f"  source: {row['conversation_title']} ({row['source_conversation_id']})")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="agentos", description="Local-first personal AI control center")
    result.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    result.add_argument("--config", type=Path, help="configuration TOML path")
    sub = result.add_subparsers(dest="command")
    sub.add_parser("status", help="show a concise system overview")
    sub.add_parser("doctor", help="check configuration and optional integrations")
    sub.add_parser("audit", help="show detailed read-only checks")
    sub.add_parser("maintain", help="suggest safe maintenance actions")
    dash = sub.add_parser("dashboard", help="generate the local HTML dashboard")
    dash.add_argument("--output", type=Path)
    migrate = sub.add_parser("migrate", help="move the legacy runtime DB into the configured data directory")
    migrate.add_argument("--json", action="store_true")
    legacy = sub.add_parser("legacy", help="run a preserved specialist workflow")
    legacy.add_argument("legacy_command")
    legacy.add_argument("arguments", nargs=argparse.REMAINDER)

    memory = sub.add_parser("memory", help="search project knowledge from ChatGPT conversations")
    memory_sub = memory.add_subparsers(dest="memory_command", required=True)
    projects = memory_sub.add_parser("projects", help="list discovered projects")
    projects.add_argument("--json", action="store_true")
    search = memory_sub.add_parser("search", help="full-text search across project knowledge")
    search.add_argument("query")
    search.add_argument("--project")
    search.add_argument("--category")
    search.add_argument("--limit", type=int, default=20)
    search.add_argument("--json", action="store_true")
    errors = memory_sub.add_parser("errors", help="search documented errors and failed approaches")
    errors.add_argument("--project")
    errors.add_argument("--limit", type=int, default=50)
    errors.add_argument("--json", action="store_true")
    reindex = memory_sub.add_parser("reindex", help="rebuild project and error indexes from extracted facts")
    reindex.add_argument("--json", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    settings = load_settings(config_path=args.config)
    command = args.command or "status"
    if command == "status":
        report = collect_status(settings)
        print(report.headline)
        _print_checks(report.checks)
        if report.suggestions:
            print("\nNext actions:")
            for suggestion in report.suggestions:
                print(f"- {suggestion}")
        return 0
    if command in {"doctor", "audit"}:
        _print_checks(doctor_checks(settings))
        return 0
    if command == "maintain":
        print("Safe maintenance suggestions (nothing was changed):")
        for suggestion in maintenance_suggestions(settings):
            print(f"- {suggestion}")
        return 0
    if command == "dashboard":
        path = render_dashboard(settings, collect_status(settings), args.output)
        print(path)
        return 0
    if command == "migrate":
        path, copied = migrate_legacy_database(settings)
        result = {"database": str(path), "copied_legacy": copied}
        print(json.dumps(result) if args.json else f"Database ready: {path} (legacy copied: {copied})")
        return 0
    if command == "legacy":
        return _legacy(settings, args.legacy_command, args.arguments)
    if command == "memory":
        return _memory_command(settings, args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
