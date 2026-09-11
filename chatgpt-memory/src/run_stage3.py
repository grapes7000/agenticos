#!/usr/bin/env python3
"""Run/resume all Stage-3 deep-memory work in bounded batches."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from chatgpt_memory import APP_ROOT, DEFAULT_MODEL, OLLAMA_HOST
from deep_memory import connect, extract_queued, link_relations, queue_conversations, write_knowledge
from deep_memory_finalize import finalize

DB_DEFAULT = APP_ROOT / "data" / "memory.sqlite3"
OUTPUT_DEFAULT = APP_ROOT / "memory"


def scalar(db: Path, sql: str) -> int:
    with connect(db) as con:
        return int(con.execute(sql).fetchone()[0])


def run_all(
    db: Path,
    model: str,
    host: str,
    batch: int,
    min_importance: int,
    output: Path,
) -> dict:
    if batch < 1:
        raise SystemExit("--batch must be >= 1")
    if not 1 <= min_importance <= 5:
        raise SystemExit("--min-importance must be 1-5")

    result = {
        "queue": queue_conversations(db, model, min_importance=min_importance),
        "batches": 0,
        "extracted": 0,
        "failed_calls": 0,
        "items": 0,
    }
    stalls = 0
    while True:
        queued = scalar(db, "SELECT count(*) FROM deep_memory_extractions WHERE state='queued'")
        if queued == 0:
            break
        print(f"deep-memory queue: {queued} passage(s) remaining", flush=True)
        before = queued
        extracted = extract_queued(db, batch, model, host)
        written = write_knowledge(db)
        linked = link_relations(db)
        result["batches"] += 1
        result["extracted"] += extracted["processed"]
        result["failed_calls"] += extracted["failed"]
        result["items"] += extracted["items"]
        result.setdefault("last_write", written)
        result.setdefault("last_link", linked)
        after = scalar(db, "SELECT count(*) FROM deep_memory_extractions WHERE state='queued'")
        if after >= before:
            stalls += 1
            if stalls >= 3:
                raise SystemExit(
                    "Stage 3 made no queue progress for three batches. "
                    "Inspect failed passages and run retry-failed before resuming."
                )
        else:
            stalls = 0

    # A final writer/link pass is cheap and makes interrupted boundaries safe.
    result["write"] = write_knowledge(db)
    result["link"] = link_relations(db)
    result["failed_passages"] = scalar(
        db, "SELECT count(*) FROM deep_memory_extractions WHERE state='failed'"
    )
    result["finalize"] = finalize(db, output)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run/resume AgenticOS ChatGPT deep memory")
    parser.add_argument("--db", type=Path, default=DB_DEFAULT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--host", default=OLLAMA_HOST)
    parser.add_argument("--batch", type=int, default=25)
    parser.add_argument("--min-importance", type=int, default=1)
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    args = parser.parse_args()
    print(json.dumps(
        run_all(args.db, args.model, args.host, args.batch, args.min_importance, args.output),
        indent=2,
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
