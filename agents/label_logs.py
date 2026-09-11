#!/usr/bin/env python3
"""Label AgenticOS markdown reports with clear intended audience banners.

This is intentionally conservative and idempotent. It inserts a visible callout
near the top of markdown files, after YAML frontmatter if present.
"""
from __future__ import annotations

import argparse
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

MARKER = "AgenticOS Audience"

USER_BANNER = """> [!success] AgenticOS Audience\n> Intended reader: **human / Brooke & Lakota**.\n> Purpose: this is a plain-English summary or map meant to be read directly.\n> Next step: use it to decide what, if anything, needs attention.\n\n"""

AI_BANNER = """> [!info] AgenticOS Audience\n> Intended reader: **AI / AgenticOS internal analysis**.\n> Human use: you do not need to manually study this unless debugging.\n> Analyzer: this file should be consumed by `agentos system` / `agentos analyze-reports`, which writes a human-facing summary and action queue.\n\n"""

MIXED_BANNER = """> [!note] AgenticOS Audience\n> Intended reader: **human + AI**.\n> Purpose: useful for review, but should also be included in `agentos system` analysis so the information is not wasted.\n\n"""

@dataclass
class LabelDecision:
    audience: str
    reason: str
    banner: str


def detect_vault() -> Path:
    env = os.environ.get("OBSIDIAN_VAULT")
    if env:
        return Path(env).expanduser()
    candidates = [
        Path.home() / "Documents" / "Obsidian Vault",
        Path.home() / "vault",
    ]
    for p in candidates:
        if (p / "Agentic OS").exists():
            return p
    return candidates[0]


def classify(path: Path, root: Path) -> LabelDecision:
    rel = str(path.relative_to(root)).lower()
    name = path.name.lower()

    user_terms = [
        "system summaries", "security summaries", "docker hardening summaries",
        "daily briefings", "daily summaries", "self-hosted services map", "home.md",
        "readme", "user summaries"
    ]
    ai_terms = [
        "security reports", "docker security reports", "docker hardening reports",
        "build quality reports", "health", "test reports", "bug reports",
        "patch plans", "work cycles", "file plans", "change reports", "raw",
        "logs", "reports/"
    ]

    if any(term in rel for term in user_terms) or name in {"self-hosted services map.md", "home.md"}:
        return LabelDecision("human", "summary/map intended for direct reading", USER_BANNER)
    if any(term in rel for term in ai_terms):
        return LabelDecision("ai", "raw report/diagnostic/planning output", AI_BANNER)
    if "summary" in rel or "summaries" in rel:
        return LabelDecision("human", "summary path", USER_BANNER)
    if "report" in rel or "plan" in rel:
        return LabelDecision("ai", "report or plan path", AI_BANNER)
    return LabelDecision("mixed", "uncategorized AgenticOS note", MIXED_BANNER)


def insert_after_frontmatter(text: str, banner: str) -> str:
    if MARKER in text[:2000]:
        return text
    lines = text.splitlines(keepends=True)
    if lines and lines[0].strip() == "---":
        for i in range(1, min(len(lines), 80)):
            if lines[i].strip() == "---":
                return "".join(lines[: i + 1]) + "\n" + banner + "".join(lines[i + 1 :])
    return banner + text


def iter_markdown(agent_root: Path) -> Iterable[Path]:
    if not agent_root.exists():
        return []
    return sorted(p for p in agent_root.rglob("*.md") if p.is_file() and ".agenticos_backups" not in str(p))


def main() -> int:
    parser = argparse.ArgumentParser(description="Label AgenticOS markdown files by audience.")
    parser.add_argument("--apply", action="store_true", help="Modify files. Without this, only preview.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes only.")
    parser.add_argument("--vault", type=str, default=None, help="Obsidian vault path.")
    args = parser.parse_args()

    vault = Path(args.vault).expanduser() if args.vault else detect_vault()
    agent_root = vault / "Agentic OS"
    backup_root = agent_root / ".agenticos_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")

    files = list(iter_markdown(agent_root))
    if not files:
        print(f"No AgenticOS markdown files found under: {agent_root}")
        return 0

    changed = 0
    for p in files:
        try:
            text = p.read_text(errors="replace")
        except Exception as exc:
            print(f"SKIP unreadable: {p} ({exc})")
            continue
        decision = classify(p, agent_root)
        already = MARKER in text[:2000]
        status = "already-labeled" if already else ("would-label" if not args.apply else "label")
        print(f"{status:15} {decision.audience:6} {p}")
        if args.apply and not already:
            rel = p.relative_to(agent_root)
            b = backup_root / rel
            b.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, b)
            p.write_text(insert_after_frontmatter(text, decision.banner))
            changed += 1

    if args.apply:
        print(f"\nLabeled {changed} file(s). Backups: {backup_root if changed else 'not needed'}")
    else:
        print("\nDry run only. Apply with: agentos label-logs --apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
