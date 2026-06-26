#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, date
from pathlib import Path
import os
import subprocess
import shlex

HOME = Path.home()
ROOT = Path(os.getenv("AGENTOS_HOME", str(HOME / "AgenticOS"))).expanduser()
VAULT = Path(os.getenv("OBSIDIAN_VAULT", str(HOME / "vault"))).expanduser()
TODAY = date.today().isoformat()
STAMP = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
OUT_DIR = VAULT / "Agentic OS" / "Build Quality Reports"
OUT_DIR.mkdir(parents=True, exist_ok=True)

EXPECTED_DIRS = ["agents", "tools", "scripts", "bin", "data", "logs"]
RISKY_PATTERNS = ["rm -rf", "chmod 777", "sudo ", "curl ", "| bash", "eval ", "mkfs", "dd if=", "wallet", "private_key", "id_rsa"]


def run(cmd: str, timeout: int = 90) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, cwd=ROOT, shell=True, text=True, capture_output=True, timeout=timeout, check=False)
        out = (r.stdout or "") + (("\nSTDERR:\n" + r.stderr) if r.stderr else "")
        return r.returncode, out.strip()
    except subprocess.TimeoutExpired:
        return 124, f"Timed out after {timeout}s: {cmd}"
    except Exception as e:
        return 999, f"Failed: {cmd}\n{e}"


def code(text: str, lang: str = "text") -> str:
    if not text.strip():
        text = "No output."
    return f"```{lang}\n{text[:20000]}\n```"


def section(title: str, body: str) -> str:
    return f"\n## {title}\n\n{body.strip() if body.strip() else '_No output._'}\n"


def command_section(title: str, cmd: str, timeout: int = 90) -> str:
    rc, out = run(cmd, timeout=timeout)
    return section(title, f"Command: `{cmd}`\n\nReturn code: `{rc}`\n\n{code(out)}")


def py_compile_section() -> str:
    py_files = []
    for folder in [ROOT / "agents", ROOT / "tools"]:
        if folder.exists():
            py_files.extend(sorted(folder.rglob("*.py")))
    if not py_files:
        return section("Python Compile Check", "No Python files found in agents/tools.")
    results = []
    failures = 0
    for p in py_files:
        rel = p.relative_to(ROOT)
        rc, out = run(f"python3 -m py_compile {shlex.quote(str(p))}", timeout=30)
        if rc != 0:
            failures += 1
        status = "PASS" if rc == 0 else "FAIL"
        results.append(f"### {status}: `{rel}`\n\n{code(out)}")
    header = f"Checked {len(py_files)} Python files. Failures: {failures}."
    return section("Python Compile Check", header + "\n\n" + "\n\n".join(results))


def shell_syntax_section() -> str:
    sh_files = []
    for folder in [ROOT / "scripts", ROOT / "bin"]:
        if folder.exists():
            for p in sorted(folder.rglob("*")):
                if p.is_file() and (p.suffix == ".sh" or os.access(p, os.X_OK)):
                    sh_files.append(p)
    if not sh_files:
        return section("Shell Syntax Check", "No shell/executable files found in scripts/bin.")
    results = []
    failures = 0
    for p in sh_files:
        rel = p.relative_to(ROOT)
        rc, out = run(f"bash -n {shlex.quote(str(p))}", timeout=30)
        if rc != 0:
            failures += 1
        status = "PASS" if rc == 0 else "FAIL"
        results.append(f"### {status}: `{rel}`\n\n{code(out)}")
    header = f"Checked {len(sh_files)} shell/executable files. Failures: {failures}."
    return section("Shell Syntax Check", header + "\n\n" + "\n\n".join(results))


def risky_patterns_section() -> str:
    matches = []
    for folder in [ROOT / "agents", ROOT / "tools", ROOT / "scripts", ROOT / "bin"]:
        if not folder.exists():
            continue
        for p in sorted(folder.rglob("*")):
            if not p.is_file():
                continue
            if p.suffix.lower() not in [".py", ".sh", ".md", ".json", ""]:
                continue
            try:
                for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
                    low = line.lower()
                    for pat in RISKY_PATTERNS:
                        if pat.lower() in low:
                            matches.append(f"{p.relative_to(ROOT)}:{i}: pattern `{pat}` → {line.strip()[:240]}")
            except Exception:
                continue
    if not matches:
        return section("Risky Pattern Scan", "No risky text patterns found in AgenticOS scripts.")
    return section("Risky Pattern Scan", "These are not automatically bad; review them.\n\n" + code("\n".join(matches)))


def expected_dirs_section() -> str:
    lines = []
    for d in EXPECTED_DIRS:
        p = ROOT / d
        lines.append(f"- {'✅' if p.exists() else '❌'} `{p}`")
    for vault_d in ["Security Reports", "Security Summaries", "Build Quality Reports", "Health", "Patch Plans", "Work Cycles"]:
        p = VAULT / "Agentic OS" / vault_d
        lines.append(f"- {'✅' if p.exists() else '❌'} `{p}`")
    return section("Expected Folders", "\n".join(lines))


def main() -> None:
    lines = [
        "---",
        "tags: [agentic-os, build-quality]",
        f"created: {TODAY}",
        f"run_id: {STAMP}",
        "---",
        "",
        f"# AgenticOS Build Quality Report - {STAMP}",
        "",
        "This report checks the local AgenticOS scripts/config structure. It does not apply fixes.",
    ]
    lines.append(expected_dirs_section())
    lines.append(command_section("AgenticOS Command Discovery", "type -a agentos; type -a agentos-work-cycle 2>/dev/null || true; agentos help", timeout=60))
    lines.append(py_compile_section())
    lines.append(shell_syntax_section())
    lines.append(command_section("AgenticOS Doctor", "agentos doctor", timeout=120))
    lines.append(command_section("AgenticOS Test", "agentos test", timeout=180))
    lines.append(command_section("AgenticOS Fix Status", "agentos fix-status", timeout=120))
    lines.append(risky_patterns_section())

    out = OUT_DIR / f"{STAMP} Build Quality Report.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote build quality report: {out}")


if __name__ == "__main__":
    main()
