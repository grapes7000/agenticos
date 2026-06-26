from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import traceback

HOME = Path.home()
AGENTOS = Path(os.getenv("AGENTOS_DIR", str(HOME / "AgenticOS"))).expanduser()
VAULT = Path(os.getenv("OBSIDIAN_VAULT", str(HOME / "vault"))).expanduser()
TODAY = datetime.now().strftime("%Y-%m-%d")
STAMP = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
DB = AGENTOS / "data" / "db" / "agent_os.sqlite"
REPORT_DIR = VAULT / "Agentic OS" / "Test Reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR = AGENTOS / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class Result:
    name: str
    status: str
    details: str = ""
    command: str = ""

@dataclass
class TestState:
    results: list[Result] = field(default_factory=list)

    def pass_(self, name: str, details: str = "", command: str = ""):
        self.results.append(Result(name, "PASS", details, command))

    def warn(self, name: str, details: str = "", command: str = ""):
        self.results.append(Result(name, "WARN", details, command))

    def fail(self, name: str, details: str = "", command: str = ""):
        self.results.append(Result(name, "FAIL", details, command))

    def run(self, name: str, fn):
        try:
            fn()
        except Exception:
            self.fail(name, traceback.format_exc())

state = TestState()

def sh(cmd: list[str], cwd: Path | None = None, timeout: int = 60, env: dict | None = None):
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(cmd, cwd=str(cwd or AGENTOS), text=True, capture_output=True, timeout=timeout, env=merged)

def test_core_dirs():
    required = [AGENTOS, AGENTOS / "agents", AGENTOS / "tools", AGENTOS / "scripts", AGENTOS / "bin", AGENTOS / "data" / "db", VAULT]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        state.fail("Core directories exist", "Missing:\n" + "\n".join(missing))
    else:
        state.pass_("Core directories exist", "AgenticOS and vault directories are present.")

def test_required_files():
    required = [
        AGENTOS / "tools" / "init_db.py",
        AGENTOS / "tools" / "scan_folder.py",
        AGENTOS / "agents" / "file_butler.py",
    ]
    optional = [
        AGENTOS / "agents" / "daily_briefing.py",
        AGENTOS / "agents" / "operator_report.py",
        AGENTOS / "agents" / "changes_report.py",
        AGENTOS / "agents" / "health_watchdog.py",
        AGENTOS / "agents" / "memory_search.py",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        state.fail("Required AgenticOS files exist", "Missing required files:\n" + "\n".join(missing))
    else:
        state.pass_("Required AgenticOS files exist", "Core scripts are present.")
    missing_optional = [p.name for p in optional if not p.exists()]
    if missing_optional:
        state.warn("Optional Layer 2/3 files", "Optional files not found: " + ", ".join(missing_optional))
    else:
        state.pass_("Optional Layer 2/3 files", "All common optional agents are present.")

def test_db_init_and_schema():
    init = AGENTOS / "tools" / "init_db.py"
    if not init.exists():
        state.fail("Database initialization", "tools/init_db.py is missing.")
        return
    proc = sh([sys.executable, str(init)], cwd=AGENTOS, timeout=60)
    if proc.returncode != 0:
        state.fail("Database initialization", proc.stderr or proc.stdout, command="python3 tools/init_db.py")
        return
    if not DB.exists():
        state.fail("Database file exists", f"Database missing after init: {DB}")
        return
    with sqlite3.connect(DB) as con:
        tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    expected = {"files", "actions", "lessons"}
    missing = sorted(expected - tables)
    if missing:
        state.fail("Database schema", "Missing tables: " + ", ".join(missing))
    else:
        state.pass_("Database schema", "files/actions/lessons tables exist.")

def test_scan_folder_with_temp_files():
    scanner = AGENTOS / "tools" / "scan_folder.py"
    if not scanner.exists():
        state.fail("Folder scanner", "tools/scan_folder.py is missing.")
        return
    tmp = Path(tempfile.mkdtemp(prefix="agentos-test-scan-"))
    try:
        (tmp / "image.png").write_bytes(b"fake image")
        (tmp / "notes.md").write_text("hello", encoding="utf-8")
        (tmp / "wallet_seed_phrase.txt").write_text("fake test secret", encoding="utf-8")
        (tmp / "script.py").write_text("print('hi')", encoding="utf-8")
        proc = sh([sys.executable, str(scanner), str(tmp)], cwd=AGENTOS, timeout=60)
        if proc.returncode != 0:
            state.fail("Folder scanner", proc.stderr or proc.stdout, command=f"python3 tools/scan_folder.py {tmp}")
            return
        with sqlite3.connect(DB) as con:
            rows = con.execute("SELECT name, category, sensitive FROM files WHERE path LIKE ?", (str(tmp) + "%",)).fetchall()
        by_name = {name: (cat, sens) for name, cat, sens in rows}
        problems = []
        if by_name.get("image.png", (None, None))[0] != "Images":
            problems.append("image.png was not categorized as Images")
        if by_name.get("script.py", (None, None))[0] != "Code":
            problems.append("script.py was not categorized as Code")
        if by_name.get("wallet_seed_phrase.txt", (None, 0))[1] != 1:
            problems.append("wallet_seed_phrase.txt was not flagged sensitive")
        if problems:
            state.fail("Folder scanner classification", "\n".join(problems))
        else:
            state.pass_("Folder scanner classification", "Scanner categorized files and flagged sensitive-looking names.")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def test_file_butler_output():
    agent = AGENTOS / "agents" / "file_butler.py"
    if not agent.exists():
        state.fail("File Butler output", "agents/file_butler.py is missing.")
        return
    env = {"OBSIDIAN_VAULT": str(VAULT)}
    proc = sh([sys.executable, str(agent)], cwd=AGENTOS, timeout=60, env=env)
    if proc.returncode != 0:
        state.fail("File Butler output", proc.stderr or proc.stdout, command="python3 agents/file_butler.py")
        return
    folder = VAULT / "Agentic OS" / "File Plans"
    notes = sorted(folder.glob("*.md")) if folder.exists() else []
    if not notes:
        state.fail("File Butler output", f"No markdown notes found in {folder}")
    else:
        newest = notes[-1]
        text = newest.read_text(encoding="utf-8", errors="replace")
        if "dry-run" in text.lower() or "dry run" in text.lower():
            state.pass_("File Butler output", f"Created dry-run note: {newest}")
        else:
            state.warn("File Butler output", f"Created note but dry-run wording not found: {newest}")

def test_cli_commands():
    agentos = AGENTOS / "bin" / "agentos"
    if not agentos.exists():
        state.warn("AgenticOS CLI", "~/AgenticOS/bin/agentos does not exist. Fallback bin commands may still work.")
        return
    if not os.access(agentos, os.X_OK):
        state.warn("AgenticOS CLI executable", "bin/agentos exists but is not executable.")
    proc = sh([str(agentos), "help"], cwd=AGENTOS, timeout=30)
    if proc.returncode == 0:
        state.pass_("AgenticOS CLI help", proc.stdout[:800])
    else:
        state.warn("AgenticOS CLI help", proc.stderr or proc.stdout)

def test_ollama_and_model():
    if shutil.which("ollama") is None:
        state.warn("Ollama availability", "ollama command not found. AI bug hunter will use fallback static checks.")
        return
    proc = sh(["ollama", "list"], cwd=AGENTOS, timeout=30)
    if proc.returncode != 0:
        state.warn("Ollama list", proc.stderr or proc.stdout)
        return
    model = os.getenv("AGENTOS_MODEL", "qwen2.5-coder:7b")
    if model.split(":")[0] in proc.stdout or model in proc.stdout:
        state.pass_("Ollama model", f"Model appears installed: {model}")
    else:
        state.warn("Ollama model", f"Model not found in ollama list: {model}\n\n{proc.stdout[:1200]}")

def test_hermes_status():
    if shutil.which("hermes") is None:
        state.warn("Hermes availability", "hermes command not found.")
        return
    proc = sh(["hermes", "cron", "list"], cwd=AGENTOS, timeout=45)
    if proc.returncode == 0:
        state.pass_("Hermes cron list", proc.stdout[:1500] or "Command succeeded with no output.")
    else:
        state.warn("Hermes cron list", proc.stderr or proc.stdout)

def test_no_dangerous_patterns():
    risky = []
    scan_dirs = [AGENTOS / "agents", AGENTOS / "tools", AGENTOS / "scripts", AGENTOS / "bin"]
    patterns = ["rm -rf /", "sudo ", "mkfs", "dd if=", "chmod -R 777 /", "curl ", "| bash"]
    for folder in scan_dirs:
        if not folder.exists():
            continue
        for path in folder.rglob("*"):
            if path.is_file() and path.stat().st_size < 400_000:
                text = path.read_text(encoding="utf-8", errors="ignore")
                for pat in patterns:
                    if pat in text:
                        risky.append(f"{path}: contains `{pat}`")
    if risky:
        # curl is not automatically a fail; installers often use it. Warn so user reviews.
        state.warn("Risky command pattern scan", "Review these occurrences:\n" + "\n".join(risky[:50]))
    else:
        state.pass_("Risky command pattern scan", "No obvious high-risk shell patterns found in AgenticOS scripts.")

def write_report():
    passed = sum(1 for r in state.results if r.status == "PASS")
    warned = sum(1 for r in state.results if r.status == "WARN")
    failed = sum(1 for r in state.results if r.status == "FAIL")

    out = REPORT_DIR / f"{STAMP} System Test Report.md"
    latest = REPORT_DIR / "latest System Test Report.md"
    log_latest = LOG_DIR / "system-test-latest.md"
    json_latest = LOG_DIR / "system-test-latest.json"

    lines = [
        "---",
        "tags: [agentic-os, tests, qa]",
        f"created: {datetime.now().isoformat(timespec='seconds')}",
        "---",
        "",
        f"# AgenticOS System Test Report - {STAMP}",
        "",
        "## Summary",
        "",
        f"- Passed: **{passed}**",
        f"- Warnings: **{warned}**",
        f"- Failed: **{failed}**",
        f"- AgenticOS: `{AGENTOS}`",
        f"- Vault: `{VAULT}`",
        "",
        "## Results",
        "",
    ]
    for r in state.results:
        emoji = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(r.status, "•")
        lines.append(f"### {emoji} {r.name}")
        lines.append("")
        lines.append(f"Status: **{r.status}**")
        lines.append("")
        if r.command:
            lines.append("Command:")
            lines.append("```bash")
            lines.append(r.command)
            lines.append("```")
        if r.details:
            lines.append("Details:")
            lines.append("```text")
            lines.append(r.details.strip()[:6000])
            lines.append("```")
        lines.append("")
    lines.extend([
        "## Suggested Next Step",
        "",
        "Run:",
        "",
        "```bash",
        "agentos bug-hunt",
        "```",
        "",
        "Then review the newest note in `Agentic OS/Bug Reports/`.",
        "",
    ])

    text = "\n".join(lines)
    for path in [out, latest, log_latest]:
        path.write_text(text, encoding="utf-8")
    json_latest.write_text(json.dumps([r.__dict__ for r in state.results], indent=2), encoding="utf-8")
    print(f"Wrote system test report: {out}")
    print(f"Latest report: {latest}")
    return failed

def main():
    tests = [
        ("Core directories", test_core_dirs),
        ("Required files", test_required_files),
        ("Database schema", test_db_init_and_schema),
        ("Folder scanner", test_scan_folder_with_temp_files),
        ("File Butler", test_file_butler_output),
        ("CLI commands", test_cli_commands),
        ("Ollama/model", test_ollama_and_model),
        ("Hermes", test_hermes_status),
        ("Risk scan", test_no_dangerous_patterns),
    ]
    for name, fn in tests:
        state.run(name, fn)
    failed = write_report()
    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
