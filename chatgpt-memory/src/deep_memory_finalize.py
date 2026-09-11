#!/usr/bin/env python3
"""Stage 3.5-3.7: conservative consolidation, conflicts, snapshots, and views.

SQLite remains canonical. Source-backed ``knowledge_items`` are never deleted or
rewritten by consolidation. This module builds rebuildable grouping/snapshot
layers over those atomic facts, records conflicts/review work separately, and
renders Markdown as a disposable view.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from chatgpt_memory import APP_ROOT, now
from deep_memory import connect, ensure_schema as ensure_deep_schema, has_table, add_relation

DB_DEFAULT = APP_ROOT / "data" / "memory.sqlite3"
MEMORY_DEFAULT = APP_ROOT / "memory"
STATE_CATEGORIES = {"configuration", "project_status", "system_state", "durable_fact", "preference"}
CURRENT_CATEGORIES = {"configuration", "project_status", "system_state", "durable_fact", "preference"}
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "by", "for", "from", "has", "have",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "was", "were", "with",
    "currently", "now", "uses", "use", "using", "set", "configured", "runs", "running",
}

FINAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS knowledge_groups(
  group_id TEXT PRIMARY KEY,
  namespace TEXT NOT NULL,
  project_slug TEXT NOT NULL REFERENCES projects(slug),
  category TEXT NOT NULL,
  state_key TEXT NOT NULL DEFAULT '',
  canonical_item_id INTEGER NOT NULL REFERENCES knowledge_items(id),
  member_count INTEGER NOT NULL,
  current_count INTEGER NOT NULL DEFAULT 0,
  cluster_context_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_knowledge_groups_scope
  ON knowledge_groups(namespace,project_slug,category,state_key);

CREATE TABLE IF NOT EXISTS knowledge_group_members(
  group_id TEXT NOT NULL REFERENCES knowledge_groups(group_id) ON DELETE CASCADE,
  item_id INTEGER NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
  member_role TEXT NOT NULL DEFAULT 'support',
  similarity REAL NOT NULL DEFAULT 1.0,
  PRIMARY KEY(group_id,item_id)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_group_members_item
  ON knowledge_group_members(item_id,group_id);

CREATE TABLE IF NOT EXISTS knowledge_conflicts(
  conflict_id TEXT PRIMARY KEY,
  namespace TEXT NOT NULL,
  project_slug TEXT NOT NULL REFERENCES projects(slug),
  category TEXT NOT NULL,
  state_key TEXT NOT NULL,
  item_a_id INTEGER NOT NULL REFERENCES knowledge_items(id),
  item_b_id INTEGER NOT NULL REFERENCES knowledge_items(id),
  reason TEXT NOT NULL,
  resolution_status TEXT NOT NULL DEFAULT 'open',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_knowledge_conflicts_status
  ON knowledge_conflicts(resolution_status,namespace,project_slug);

CREATE TABLE IF NOT EXISTS knowledge_review_queue(
  review_id INTEGER PRIMARY KEY,
  stable_key TEXT UNIQUE NOT NULL,
  kind TEXT NOT NULL,
  namespace TEXT NOT NULL DEFAULT 'unknown',
  project_slug TEXT NOT NULL DEFAULT '',
  item_id INTEGER REFERENCES knowledge_items(id),
  related_item_id INTEGER REFERENCES knowledge_items(id),
  reason TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  created_at TEXT NOT NULL,
  resolved_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_knowledge_review_status
  ON knowledge_review_queue(status,kind);

CREATE TABLE IF NOT EXISTS knowledge_overrides(
  stable_key TEXT PRIMARY KEY,
  action TEXT NOT NULL,
  value_json TEXT NOT NULL DEFAULT '{}',
  reason TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS project_memory_snapshots(
  namespace TEXT NOT NULL,
  project_slug TEXT NOT NULL REFERENCES projects(slug),
  snapshot_hash TEXT NOT NULL,
  current_json TEXT NOT NULL DEFAULT '[]',
  decisions_json TEXT NOT NULL DEFAULT '[]',
  configuration_json TEXT NOT NULL DEFAULT '[]',
  errors_json TEXT NOT NULL DEFAULT '[]',
  workflows_json TEXT NOT NULL DEFAULT '[]',
  history_json TEXT NOT NULL DEFAULT '[]',
  conflicts_json TEXT NOT NULL DEFAULT '[]',
  cluster_context_json TEXT NOT NULL DEFAULT '[]',
  generated_at TEXT NOT NULL,
  PRIMARY KEY(namespace,project_slug)
);
"""


def ensure_finalize_schema(db: Path) -> None:
    ensure_deep_schema(db)
    with connect(db) as con:
        con.executescript(FINAL_SCHEMA)


def stable_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def normalize_statement(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"`+", "", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^a-z0-9_./:+#@-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def state_key(statement: str) -> str:
    """Conservative topic key used only to find possible state conflicts.

    Numbers and common linking verbs are omitted so e.g. ``SSH port is 22`` and
    ``SSH port is 2222`` share a key. The key never proves two claims conflict;
    it only narrows candidates for review.
    """
    tokens = re.findall(r"[a-z][a-z0-9_.:/+-]*", statement.lower())
    useful = [t for t in tokens if t not in STOPWORDS and not t.isdigit()]
    return " ".join(useful[:5])


def confidence_value(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        text = str(value or "").upper()
        return {"HIGH": .9, "MEDIUM": .65, "LOW": .35}.get(text, .5)


def date_key(value: str | None) -> str:
    return str(value or "")


def override_map(con: sqlite3.Connection) -> dict[str, sqlite3.Row]:
    return {str(row["stable_key"]): row for row in con.execute("SELECT * FROM knowledge_overrides")}


def effective_status(item: sqlite3.Row, overrides: dict[str, sqlite3.Row]) -> str:
    override = overrides.get(f"force_status:{item['id']}")
    if override and override["action"] == "force_status":
        try:
            status = str(json.loads(override["value_json"]).get("status", "")).lower()
        except (TypeError, json.JSONDecodeError):
            status = ""
        if status in {"current", "historical", "superseded", "unknown"}:
            return status
    status = str(item["status"] or "unknown").lower()
    return status if status in {"current", "historical", "superseded", "unknown"} else "unknown"


def item_suppressed(item_id: int, overrides: dict[str, sqlite3.Row]) -> bool:
    row = overrides.get(f"suppress_item:{item_id}")
    return bool(row and row["action"] == "suppress_item")


def item_projects(con: sqlite3.Connection) -> dict[int, set[str]]:
    result: dict[int, set[str]] = defaultdict(set)
    if has_table(con, "knowledge_item_projects"):
        for row in con.execute("SELECT knowledge_item_id,project_slug FROM knowledge_item_projects"):
            result[int(row["knowledge_item_id"])].add(str(row["project_slug"]))
    for row in con.execute("SELECT id,project_slug FROM knowledge_items WHERE origin='stage3'"):
        result[int(row["id"])].add(str(row["project_slug"]))
    return result


def latest_global_cluster_map(con: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    if not (has_table(con, "semantic_cluster_runs") and has_table(con, "conversation_reductions")):
        return {}
    run_id = None
    for row in con.execute("SELECT run_id,scope_json FROM semantic_cluster_runs ORDER BY created_at DESC"):
        try:
            scope = json.loads(row["scope_json"])
        except (TypeError, json.JSONDecodeError):
            continue
        if not scope.get("identity") and not scope.get("conversation_type"):
            run_id = str(row["run_id"])
            break
    if not run_id:
        return {}
    labels: dict[int, str] = {}
    if has_table(con, "semantic_clusters"):
        for row in con.execute(
            "SELECT cluster_id,COALESCE(label,'') AS label FROM semantic_clusters WHERE run_id=?", (run_id,)
        ):
            labels[int(row["cluster_id"])] = str(row["label"] or "")
    result: dict[str, dict[str, Any]] = {}
    for row in con.execute(
        "SELECT conversation_id,cluster_id FROM conversation_reductions WHERE run_id=?", (run_id,)
    ):
        cluster_id = int(row["cluster_id"])
        if cluster_id < 0:
            continue
        result[str(row["conversation_id"])] = {
            "run_id": run_id,
            "cluster_id": cluster_id,
            "label": labels.get(cluster_id, ""),
        }
    return result


def evidence_sources(con: sqlite3.Connection, item_id: int) -> list[dict[str, Any]]:
    rows = con.execute(
        """SELECT conversation_id,passage_ref,evidence_ref,source_date
           FROM knowledge_evidence WHERE knowledge_item_id=? ORDER BY source_date,conversation_id,passage_ref""",
        (item_id,),
    ).fetchall()
    if rows:
        return [dict(row) for row in rows]
    row = con.execute(
        "SELECT source_conversation_id,source_date FROM knowledge_items WHERE id=?", (item_id,)
    ).fetchone()
    return ([{
        "conversation_id": row["source_conversation_id"],
        "passage_ref": "",
        "evidence_ref": "",
        "source_date": row["source_date"],
    }] if row else [])


def item_cluster_context(
    con: sqlite3.Connection,
    item_ids: Iterable[int],
    cluster_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    counts: Counter[tuple[int, str, str]] = Counter()
    for item_id in item_ids:
        for source in evidence_sources(con, int(item_id)):
            ctx = cluster_map.get(str(source["conversation_id"]))
            if not ctx:
                continue
            counts[(int(ctx["cluster_id"]), str(ctx["label"]), str(ctx["run_id"]))] += 1
    return [
        {"cluster_id": cid, "label": label, "run_id": run_id, "support_count": count}
        for (cid, label, run_id), count in counts.most_common()
    ]


def similarity(a: str, b: str) -> float:
    if a == b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def choose_canonical(items: list[sqlite3.Row], overrides: dict[str, sqlite3.Row]) -> sqlite3.Row:
    status_rank = {"current": 4, "unknown": 3, "historical": 2, "superseded": 1}
    return max(
        items,
        key=lambda row: (
            status_rank.get(effective_status(row, overrides), 0),
            confidence_value(row["confidence"]),
            date_key(row["source_date"]),
            int(row["id"]),
        ),
    )


def group_scope_items(items: list[sqlite3.Row], category: str) -> list[list[tuple[sqlite3.Row, float]]]:
    """Conservatively group exact/very-near duplicate claims.

    Claims with no useful state key are only grouped when their normalized text
    is exactly equal. State-like claims may group at >= .94 text similarity, but
    distinct values remain separate and can later become conflicts.
    """
    groups: list[list[tuple[sqlite3.Row, float]]] = []
    representatives: list[str] = []
    rep_keys: list[str] = []
    for item in items:
        norm = normalize_statement(str(item["statement"]))
        key = state_key(str(item["statement"])) if category in STATE_CATEGORIES else ""
        matched = None
        matched_score = 0.0
        for idx, rep in enumerate(representatives):
            if norm == rep:
                matched, matched_score = idx, 1.0
                break
            if key and key == rep_keys[idx]:
                score = similarity(norm, rep)
                if score >= .94 and score > matched_score:
                    matched, matched_score = idx, score
        if matched is None:
            groups.append([(item, 1.0)])
            representatives.append(norm)
            rep_keys.append(key)
        else:
            groups[matched].append((item, matched_score))
    return groups


def upsert_review(
    con: sqlite3.Connection,
    stable_key: str,
    kind: str,
    namespace: str,
    project_slug: str,
    reason: str,
    item_id: int | None = None,
    related_item_id: int | None = None,
) -> None:
    con.execute(
        """INSERT INTO knowledge_review_queue
           (stable_key,kind,namespace,project_slug,item_id,related_item_id,reason,status,created_at)
           VALUES(?,?,?,?,?,?,?,'open',?)
           ON CONFLICT(stable_key) DO UPDATE SET
             kind=excluded.kind,namespace=excluded.namespace,project_slug=excluded.project_slug,
             item_id=excluded.item_id,related_item_id=excluded.related_item_id,reason=excluded.reason,
             status=CASE WHEN knowledge_review_queue.status='resolved' THEN 'resolved' ELSE 'open' END""",
        (stable_key, kind, namespace, project_slug, item_id, related_item_id, reason[:1000], now()),
    )


def build_groups(db: Path) -> dict[str, int]:
    ensure_finalize_schema(db)
    stats = {"groups": 0, "members": 0, "conflicts": 0, "reviews": 0, "supersedes": 0}
    with connect(db) as con:
        overrides = override_map(con)
        projects = item_projects(con)
        cluster_map = latest_global_cluster_map(con)
        items = con.execute(
            "SELECT * FROM knowledge_items WHERE origin='stage3' ORDER BY namespace,category,source_date,id"
        ).fetchall()
        # Rebuildable consolidation layer only. Atomic facts/evidence are untouched.
        con.execute("DELETE FROM knowledge_group_members")
        con.execute("DELETE FROM knowledge_groups")
        scopes: dict[tuple[str, str, str], list[sqlite3.Row]] = defaultdict(list)
        for item in items:
            iid = int(item["id"])
            if item_suppressed(iid, overrides):
                continue
            for project_slug in sorted(projects.get(iid) or {str(item["project_slug"])}):
                scopes[(str(item["namespace"]), project_slug, str(item["category"]))].append(item)

        item_group: dict[tuple[int, str], str] = {}
        for (namespace, project_slug, category), scoped in scopes.items():
            for grouped in group_scope_items(scoped, category):
                group_items = [row for row, _ in grouped]
                canonical = choose_canonical(group_items, overrides)
                canonical_norm = normalize_statement(str(canonical["statement"]))
                skey = state_key(str(canonical["statement"])) if category in STATE_CATEGORIES else ""
                group_id = "kg-" + stable_hash({
                    "namespace": namespace,
                    "project": project_slug,
                    "category": category,
                    "canonical": canonical_norm,
                })[:16]
                context = item_cluster_context(con, [int(row["id"]) for row in group_items], cluster_map)
                current_count = sum(effective_status(row, overrides) == "current" for row in group_items)
                con.execute(
                    """INSERT INTO knowledge_groups
                       (group_id,namespace,project_slug,category,state_key,canonical_item_id,
                        member_count,current_count,cluster_context_json,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        group_id, namespace, project_slug, category, skey, int(canonical["id"]),
                        len(group_items), current_count, json.dumps(context, ensure_ascii=False), now(), now(),
                    ),
                )
                for row, score in grouped:
                    status = effective_status(row, overrides)
                    role = "canonical" if int(row["id"]) == int(canonical["id"]) else (
                        "superseded" if status == "superseded" else "historical" if status == "historical" else "support"
                    )
                    con.execute(
                        "INSERT INTO knowledge_group_members(group_id,item_id,member_role,similarity) VALUES(?,?,?,?)",
                        (group_id, int(row["id"]), role, float(score)),
                    )
                    item_group[(int(row["id"]), project_slug)] = group_id
                    stats["members"] += 1
                stats["groups"] += 1

        # Blocked candidates are reviewable evidence, not silently discarded.
        if has_table(con, "deep_memory_candidates"):
            for row in con.execute(
                """SELECT candidate_id,namespace,promotion_state,statement
                   FROM deep_memory_candidates
                   WHERE promotion_state LIKE 'blocked_%'"""
            ):
                key = f"candidate:{row['candidate_id']}"
                before = con.execute(
                    "SELECT 1 FROM knowledge_review_queue WHERE stable_key=?", (key,)
                ).fetchone()
                upsert_review(
                    con, key, str(row["promotion_state"]), str(row["namespace"]), "",
                    f"Candidate retained for review: {row['statement']}",
                )
                if not before:
                    stats["reviews"] += 1

        # Potential state conflicts are only compared inside the same
        # namespace/project/category/state-key scope.
        state_scopes: dict[tuple[str, str, str, str], list[sqlite3.Row]] = defaultdict(list)
        for (namespace, project_slug, category), scoped in scopes.items():
            if category not in STATE_CATEGORIES:
                continue
            for item in scoped:
                key = state_key(str(item["statement"]))
                if key:
                    state_scopes[(namespace, project_slug, category, key)].append(item)

        seen_conflicts: set[str] = set()
        for (namespace, project_slug, category, skey), values in state_scopes.items():
            # Compare only canonical representatives of distinct duplicate groups.
            reps: dict[str, sqlite3.Row] = {}
            for item in values:
                gid = item_group.get((int(item["id"]), project_slug))
                if not gid:
                    continue
                group = con.execute(
                    "SELECT canonical_item_id FROM knowledge_groups WHERE group_id=?", (gid,)
                ).fetchone()
                if group:
                    canonical = con.execute(
                        "SELECT * FROM knowledge_items WHERE id=?", (group["canonical_item_id"],)
                    ).fetchone()
                    if canonical:
                        reps[gid] = canonical
            rep_values = list(reps.values())
            for i, left in enumerate(rep_values):
                for right in rep_values[i + 1:]:
                    if normalize_statement(str(left["statement"])) == normalize_statement(str(right["statement"])):
                        continue
                    a, b = sorted((int(left["id"]), int(right["id"])))
                    ls, rs = effective_status(left, overrides), effective_status(right, overrides)
                    # Explicit historical/superseded evidence can establish a
                    # transition; chronology only chooses direction after that.
                    if {ls, rs} & {"historical", "superseded"} and "current" in {ls, rs}:
                        current = left if ls == "current" else right
                        older = right if current is left else left
                        stats["supersedes"] += add_relation(
                            con, int(current["id"]), "supersedes", int(older["id"]),
                            "Explicit current versus historical/superseded Stage-3 state",
                        )
                        continue
                    conflict_id = "kc-" + stable_hash({
                        "namespace": namespace, "project": project_slug, "category": category,
                        "state_key": skey, "a": a, "b": b,
                    })[:16]
                    seen_conflicts.add(conflict_id)
                    resolution = "open"
                    override = overrides.get(f"resolve_conflict:{conflict_id}")
                    if override and override["action"] == "resolve_conflict":
                        resolution = "resolved_override"
                    reason = (
                        "Distinct current claims share the same state key" if ls == rs == "current"
                        else "Possible state conflict needs explicit temporal evidence"
                    )
                    con.execute(
                        """INSERT INTO knowledge_conflicts
                           (conflict_id,namespace,project_slug,category,state_key,item_a_id,item_b_id,
                            reason,resolution_status,created_at,updated_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?)
                           ON CONFLICT(conflict_id) DO UPDATE SET
                             reason=excluded.reason,resolution_status=excluded.resolution_status,
                             updated_at=excluded.updated_at""",
                        (conflict_id, namespace, project_slug, category, skey, a, b, reason, resolution, now(), now()),
                    )
                    if resolution == "open":
                        review_key = f"conflict:{conflict_id}"
                        before = con.execute(
                            "SELECT 1 FROM knowledge_review_queue WHERE stable_key=?", (review_key,)
                        ).fetchone()
                        upsert_review(con, review_key, "state_conflict", namespace, project_slug, reason, a, b)
                        if not before:
                            stats["reviews"] += 1
                        stats["conflicts"] += 1
        # Close stale auto-generated conflicts without deleting their history.
        for row in con.execute("SELECT conflict_id FROM knowledge_conflicts WHERE resolution_status='open'"):
            if str(row["conflict_id"]) not in seen_conflicts:
                con.execute(
                    "UPDATE knowledge_conflicts SET resolution_status='stale',updated_at=? WHERE conflict_id=?",
                    (now(), row["conflict_id"]),
                )
    return stats


def relation_targets(con: sqlite3.Connection, item_id: int) -> list[dict[str, Any]]:
    rows = con.execute(
        """SELECT kr.relation,ki.id,ki.category,ki.statement,ki.status
           FROM knowledge_relations kr JOIN knowledge_items ki ON ki.id=kr.target_item_id
           WHERE kr.source_item_id=? ORDER BY kr.relation,ki.id""",
        (item_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def group_record(
    con: sqlite3.Connection,
    group: sqlite3.Row,
    overrides: dict[str, sqlite3.Row],
) -> dict[str, Any]:
    item = con.execute("SELECT * FROM knowledge_items WHERE id=?", (group["canonical_item_id"],)).fetchone()
    if not item:
        return {}
    members = [int(row[0]) for row in con.execute(
        "SELECT item_id FROM knowledge_group_members WHERE group_id=? ORDER BY item_id", (group["group_id"],)
    )]
    sources: list[dict[str, Any]] = []
    seen_sources: set[tuple[str, str, str]] = set()
    for item_id in members:
        for source in evidence_sources(con, item_id):
            key = (str(source["conversation_id"]), str(source["passage_ref"]), str(source["evidence_ref"]))
            if key not in seen_sources:
                seen_sources.add(key)
                sources.append(source)
    try:
        clusters = json.loads(group["cluster_context_json"] or "[]")
    except (TypeError, json.JSONDecodeError):
        clusters = []
    return {
        "group_id": group["group_id"],
        "item_id": int(item["id"]),
        "category": item["category"],
        "statement": item["statement"],
        "status": effective_status(item, overrides),
        "confidence": confidence_value(item["confidence"]),
        "source_date": item["source_date"],
        "member_count": int(group["member_count"]),
        "sources": sources,
        "clusters": clusters,
        "relations": relation_targets(con, int(item["id"])),
    }


def build_snapshots(db: Path) -> dict[str, int]:
    ensure_finalize_schema(db)
    stats = {"snapshots": 0, "projects": 0}
    with connect(db) as con:
        overrides = override_map(con)
        scopes = con.execute(
            "SELECT DISTINCT namespace,project_slug FROM knowledge_groups ORDER BY namespace,project_slug"
        ).fetchall()
        for scope in scopes:
            namespace, project_slug = str(scope["namespace"]), str(scope["project_slug"])
            groups = con.execute(
                """SELECT * FROM knowledge_groups WHERE namespace=? AND project_slug=?
                   ORDER BY category,state_key,group_id""",
                (namespace, project_slug),
            ).fetchall()
            records = [group_record(con, group, overrides) for group in groups]
            records = [record for record in records if record]
            current = [
                r for r in records
                if r["category"] in CURRENT_CATEGORIES and r["status"] in {"current", "unknown"}
            ]
            decisions = [r for r in records if r["category"] in {"decision", "decision_reason"}]
            configuration = [r for r in records if r["category"] == "configuration"]
            workflows = [r for r in records if r["category"] in {"workflow", "lesson"}]
            history = [r for r in records if r["status"] in {"historical", "superseded"}]
            errors: list[dict[str, Any]] = []
            for record in records:
                if record["category"] == "error":
                    errors.append(record)
            conflicts = [dict(row) for row in con.execute(
                """SELECT conflict_id,category,state_key,item_a_id,item_b_id,reason,resolution_status
                   FROM knowledge_conflicts WHERE namespace=? AND project_slug=?
                   ORDER BY resolution_status,category,state_key""",
                (namespace, project_slug),
            )]
            cluster_counter: Counter[tuple[int, str, str]] = Counter()
            for record in records:
                for ctx in record["clusters"]:
                    cluster_counter[(int(ctx["cluster_id"]), str(ctx.get("label", "")), str(ctx.get("run_id", "")))] += int(ctx.get("support_count", 1))
            cluster_context = [
                {"cluster_id": cid, "label": label, "run_id": run_id, "support_count": count}
                for (cid, label, run_id), count in cluster_counter.most_common()
            ]
            payload = {
                "current": current,
                "decisions": decisions,
                "configuration": configuration,
                "errors": errors,
                "workflows": workflows,
                "history": history,
                "conflicts": conflicts,
                "clusters": cluster_context,
            }
            snapshot_hash = stable_hash(payload)
            con.execute(
                """INSERT INTO project_memory_snapshots
                   (namespace,project_slug,snapshot_hash,current_json,decisions_json,configuration_json,
                    errors_json,workflows_json,history_json,conflicts_json,cluster_context_json,generated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(namespace,project_slug) DO UPDATE SET
                     snapshot_hash=excluded.snapshot_hash,current_json=excluded.current_json,
                     decisions_json=excluded.decisions_json,configuration_json=excluded.configuration_json,
                     errors_json=excluded.errors_json,workflows_json=excluded.workflows_json,
                     history_json=excluded.history_json,conflicts_json=excluded.conflicts_json,
                     cluster_context_json=excluded.cluster_context_json,generated_at=excluded.generated_at""",
                (
                    namespace, project_slug, snapshot_hash,
                    json.dumps(current, ensure_ascii=False), json.dumps(decisions, ensure_ascii=False),
                    json.dumps(configuration, ensure_ascii=False), json.dumps(errors, ensure_ascii=False),
                    json.dumps(workflows, ensure_ascii=False), json.dumps(history, ensure_ascii=False),
                    json.dumps(conflicts, ensure_ascii=False), json.dumps(cluster_context, ensure_ascii=False), now(),
                ),
            )
            stats["snapshots"] += 1
        stats["projects"] = len({str(row["project_slug"]) for row in scopes})
    return stats


def source_suffix(record: dict[str, Any]) -> str:
    sources = record.get("sources") or []
    if not sources:
        return ""
    refs = []
    for source in sources[:6]:
        cid = source.get("conversation_id", "")
        passage = source.get("passage_ref", "")
        evidence = source.get("evidence_ref", "")
        suffix = "#" + "/".join(x for x in (passage, evidence) if x) if passage or evidence else ""
        refs.append(f"`chatgpt://conversation/{cid}{suffix}`")
    extra = len(sources) - len(refs)
    if extra > 0:
        refs.append(f"+{extra} more")
    return " — " + ", ".join(refs)


def record_lines(records: list[dict[str, Any]], empty: str = "No items.") -> list[str]:
    if not records:
        return [empty, ""]
    lines: list[str] = []
    for record in records:
        status = record.get("status", "unknown")
        confidence = float(record.get("confidence", .5))
        lines.append(f"- **[{status}]** {record.get('statement','')} _(confidence {confidence:.2f})_{source_suffix(record)}")
        relations = record.get("relations") or []
        for relation in relations:
            lines.append(f"  - `{relation['relation']}` → {relation['statement']}")
    lines.append("")
    return lines


def render_project(db: Path, output: Path, namespace: str, project_slug: str) -> Path:
    with connect(db) as con:
        project = con.execute("SELECT name FROM projects WHERE slug=?", (project_slug,)).fetchone()
        snap = con.execute(
            "SELECT * FROM project_memory_snapshots WHERE namespace=? AND project_slug=?",
            (namespace, project_slug),
        ).fetchone()
    if not snap:
        raise ValueError(f"missing snapshot for {namespace}/{project_slug}")
    name = str(project["name"] if project else project_slug)
    folder = output / namespace / "projects" / project_slug
    folder.mkdir(parents=True, exist_ok=True)
    def load(column: str) -> list[Any]:
        try:
            value = json.loads(snap[column] or "[]")
        except json.JSONDecodeError:
            value = []
        return value if isinstance(value, list) else []
    current, decisions = load("current_json"), load("decisions_json")
    configuration, errors = load("configuration_json"), load("errors_json")
    workflows, history = load("workflows_json"), load("history_json")
    conflicts, clusters = load("conflicts_json"), load("cluster_context_json")

    readme = [
        f"# {name}", "", f"Namespace: `{namespace}`", "",
        "Generated from source-backed SQLite memory. This directory is a rebuildable view, not the source of truth.", "",
        "## Snapshot", "",
        f"- Current/state items: {len(current)}",
        f"- Decisions: {len(decisions)}",
        f"- Configuration items: {len(configuration)}",
        f"- Error chains: {len(errors)}",
        f"- Workflows/lessons: {len(workflows)}",
        f"- Historical/superseded items: {len(history)}",
        f"- Conflicts: {len(conflicts)}", "",
        "## Files", "",
        "- [Current state](CURRENT_STATE.md)",
        "- [Decisions](DECISIONS.md)",
        "- [Configuration](CONFIGURATION.md)",
        "- [Errors and fixes](ERRORS_AND_FIXES.md)",
        "- [Workflows](WORKFLOWS.md)",
        "- [History](HISTORY.md)",
        "- [Conflicts](CONFLICTS.md)", "",
    ]
    if clusters:
        readme.extend(["## Semantic context", ""])
        for ctx in clusters[:12]:
            label = ctx.get("label") or f"cluster {ctx.get('cluster_id')}"
            readme.append(f"- {label}: {ctx.get('support_count', 0)} source link(s)")
        readme.append("")
    (folder / "README.md").write_text("\n".join(readme), encoding="utf-8")

    docs = {
        "CURRENT_STATE.md": ("Current State", current),
        "DECISIONS.md": ("Decisions", decisions),
        "CONFIGURATION.md": ("Configuration", configuration),
        "ERRORS_AND_FIXES.md": ("Errors and Fixes", errors),
        "WORKFLOWS.md": ("Workflows and Lessons", workflows),
        "HISTORY.md": ("History", history),
    }
    for filename, (title, records) in docs.items():
        lines = [f"# {name} — {title}", "", "Generated view. SQLite is canonical.", ""]
        lines.extend(record_lines(records))
        (folder / filename).write_text("\n".join(lines), encoding="utf-8")

    conflict_lines = [f"# {name} — Conflicts", "", "Unresolved contradictions are preserved rather than guessed away.", ""]
    if conflicts:
        for conflict in conflicts:
            conflict_lines.extend([
                f"## {conflict.get('conflict_id')}", "",
                f"- Status: `{conflict.get('resolution_status')}`",
                f"- Category: `{conflict.get('category')}`",
                f"- State key: `{conflict.get('state_key')}`",
                f"- Items: `{conflict.get('item_a_id')}` vs `{conflict.get('item_b_id')}`",
                f"- Reason: {conflict.get('reason')}", "",
            ])
    else:
        conflict_lines.extend(["No recorded conflicts.", ""])
    (folder / "CONFLICTS.md").write_text("\n".join(conflict_lines), encoding="utf-8")
    return folder


def render_all(db: Path, output: Path = MEMORY_DEFAULT) -> dict[str, int]:
    ensure_finalize_schema(db)
    output.mkdir(parents=True, exist_ok=True)
    stats = {"projects": 0, "files": 0}
    with connect(db) as con:
        rows = con.execute(
            "SELECT namespace,project_slug FROM project_memory_snapshots ORDER BY namespace,project_slug"
        ).fetchall()
    for row in rows:
        render_project(db, output, str(row["namespace"]), str(row["project_slug"]))
        stats["projects"] += 1
        stats["files"] += 8
    return stats


def add_override(db: Path, key: str, action: str, value: dict[str, Any], reason: str) -> None:
    ensure_finalize_schema(db)
    with connect(db) as con:
        con.execute(
            """INSERT INTO knowledge_overrides(stable_key,action,value_json,reason,created_at,updated_at)
               VALUES(?,?,?,?,?,?)
               ON CONFLICT(stable_key) DO UPDATE SET action=excluded.action,value_json=excluded.value_json,
                 reason=excluded.reason,updated_at=excluded.updated_at""",
            (key, action, json.dumps(value, ensure_ascii=False, sort_keys=True), reason, now(), now()),
        )


def review_status(db: Path) -> dict[str, Any]:
    ensure_finalize_schema(db)
    with connect(db) as con:
        return {
            "groups": int(con.execute("SELECT count(*) FROM knowledge_groups").fetchone()[0]),
            "group_members": int(con.execute("SELECT count(*) FROM knowledge_group_members").fetchone()[0]),
            "conflicts": {
                row["resolution_status"]: int(row["n"])
                for row in con.execute("SELECT resolution_status,count(*) AS n FROM knowledge_conflicts GROUP BY resolution_status")
            },
            "review": {
                row["status"]: int(row["n"])
                for row in con.execute("SELECT status,count(*) AS n FROM knowledge_review_queue GROUP BY status")
            },
            "overrides": int(con.execute("SELECT count(*) FROM knowledge_overrides").fetchone()[0]),
            "snapshots": int(con.execute("SELECT count(*) FROM project_memory_snapshots").fetchone()[0]),
        }


def finalize(db: Path, output: Path | None = None) -> dict[str, Any]:
    groups = build_groups(db)
    snapshots = build_snapshots(db)
    rendered = render_all(db, output or MEMORY_DEFAULT)
    return {"groups": groups, "snapshots": snapshots, "render": rendered, "status": review_status(db)}


def parse_value(value: str) -> dict[str, Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("override value must be a JSON object")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize AgenticOS Stage-3 deep memory")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="dedupe/group, detect conflicts, snapshot, and render")
    run.add_argument("--db", type=Path, default=DB_DEFAULT)
    run.add_argument("--output", type=Path, default=MEMORY_DEFAULT)

    group = sub.add_parser("group", help="rebuild conservative duplicate groups/conflicts/review queue")
    group.add_argument("--db", type=Path, default=DB_DEFAULT)

    snapshot = sub.add_parser("snapshot", help="rebuild project/cluster snapshots")
    snapshot.add_argument("--db", type=Path, default=DB_DEFAULT)

    render = sub.add_parser("render", help="render Markdown views from snapshots")
    render.add_argument("--db", type=Path, default=DB_DEFAULT)
    render.add_argument("--output", type=Path, default=MEMORY_DEFAULT)

    status = sub.add_parser("status")
    status.add_argument("--db", type=Path, default=DB_DEFAULT)

    override = sub.add_parser("override", help="store a durable consolidation correction")
    override.add_argument("key")
    override.add_argument("action", choices=["suppress_item", "force_status", "resolve_conflict"])
    override.add_argument("--value", type=parse_value, default={})
    override.add_argument("--reason", required=True)
    override.add_argument("--db", type=Path, default=DB_DEFAULT)

    args = parser.parse_args()
    if args.command == "run":
        print(json.dumps(finalize(args.db, args.output), indent=2, sort_keys=True))
    elif args.command == "group":
        print(json.dumps(build_groups(args.db), indent=2, sort_keys=True))
    elif args.command == "snapshot":
        print(json.dumps(build_snapshots(args.db), indent=2, sort_keys=True))
    elif args.command == "render":
        print(json.dumps(render_all(args.db, args.output), indent=2, sort_keys=True))
    elif args.command == "status":
        print(json.dumps(review_status(args.db), indent=2, sort_keys=True))
    else:
        add_override(args.db, args.key, args.action, args.value, args.reason)
        print(f"stored override {args.key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
