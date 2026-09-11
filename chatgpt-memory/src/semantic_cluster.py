#!/usr/bin/env python3
"""Semantic discovery over archived ChatGPT conversation embeddings.

Reads chunk embeddings directly from SQLite, builds one normalized vector per
conversation, reduces with PCA then UMAP, clusters the UMAP representation with
DBSCAN, and stores the result back in SQLite. A second 2-D UMAP is retained only
for visualization/export; clustering is performed in the higher-dimensional
UMAP space.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

from chatgpt_memory import APP_ROOT, connect, now
from chatgpt_archive import ensure_schema as ensure_archive_schema

DB_DEFAULT = APP_ROOT / "data" / "memory.sqlite3"


def imports():
    try:
        import numpy as np
        from sklearn.cluster import DBSCAN
        from sklearn.decomposition import PCA
        import umap
    except ImportError as exc:
        raise SystemExit(
            "Missing clustering dependencies. Install with:\n"
            "  python3 -m pip install numpy scikit-learn umap-learn\n"
            f"Original error: {exc}"
        )
    return np, PCA, DBSCAN, umap


def ensure_cluster_schema(db: Path) -> None:
    ensure_archive_schema(db)
    with connect(db) as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS semantic_cluster_runs(
              run_id TEXT PRIMARY KEY,
              created_at TEXT NOT NULL,
              scope_json TEXT NOT NULL,
              embedding_model TEXT,
              sample_count INTEGER NOT NULL,
              vector_dimensions INTEGER NOT NULL,
              pca_dimensions INTEGER NOT NULL,
              umap_dimensions INTEGER NOT NULL,
              eps REAL NOT NULL,
              min_samples INTEGER NOT NULL,
              cluster_count INTEGER NOT NULL,
              noise_count INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS conversation_reductions(
              run_id TEXT NOT NULL REFERENCES semantic_cluster_runs(run_id) ON DELETE CASCADE,
              conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id),
              cluster_id INTEGER NOT NULL,
              pca_json TEXT NOT NULL,
              umap_json TEXT NOT NULL,
              vis_x REAL NOT NULL,
              vis_y REAL NOT NULL,
              PRIMARY KEY(run_id,conversation_id)
            );
            CREATE INDEX IF NOT EXISTS idx_conversation_reductions_cluster
              ON conversation_reductions(run_id,cluster_id);
            CREATE TABLE IF NOT EXISTS semantic_clusters(
              run_id TEXT NOT NULL REFERENCES semantic_cluster_runs(run_id) ON DELETE CASCADE,
              cluster_id INTEGER NOT NULL,
              size INTEGER NOT NULL,
              label TEXT,
              description TEXT,
              PRIMARY KEY(run_id,cluster_id)
            );
            """
        )


def _norm(np, vector):
    n = float(np.linalg.norm(vector))
    return vector / n if n > 0 else vector


def load_conversation_vectors(
    db: Path,
    identity: str | None = None,
    conversation_type: str | None = None,
):
    np, _, _, _ = imports()
    ensure_cluster_schema(db)

    where = ["cc.embedding_json IS NOT NULL"]
    params: list[Any] = []
    joins = []
    if identity:
        joins.append("JOIN identity_classifications i ON i.conversation_id=cc.conversation_id")
        where.append("i.identity=?")
        params.append(identity.upper())
    if conversation_type:
        joins.append("JOIN conversation_organizations o ON o.conversation_id=cc.conversation_id")
        where.append("o.conversation_type=?")
        params.append(conversation_type)

    sql = f"""
        SELECT cc.conversation_id,cc.chunk_index,cc.embedding_json,cc.embedding_model
        FROM chat_chunks cc
        {' '.join(joins)}
        WHERE {' AND '.join(where)}
        ORDER BY cc.conversation_id,cc.chunk_index
    """
    grouped: dict[str, list[Any]] = defaultdict(list)
    models: dict[str, int] = defaultdict(int)
    dimensions: int | None = None

    with connect(db) as con:
        rows = con.execute(sql, params).fetchall()
    for row in rows:
        try:
            arr = np.asarray(json.loads(row["embedding_json"]), dtype=np.float32)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if arr.ndim != 1 or arr.size == 0 or not np.isfinite(arr).all():
            continue
        if dimensions is None:
            dimensions = int(arr.size)
        if arr.size != dimensions:
            continue
        grouped[row["conversation_id"]].append(_norm(np, arr))
        if row["embedding_model"]:
            models[str(row["embedding_model"])] += 1

    ids: list[str] = []
    vectors: list[Any] = []
    for cid, chunks in grouped.items():
        if not chunks:
            continue
        mean = np.mean(np.vstack(chunks), axis=0)
        ids.append(cid)
        vectors.append(_norm(np, mean))

    if not vectors:
        raise SystemExit("No usable conversation embeddings found for this scope.")
    matrix = np.vstack(vectors).astype(np.float32)
    model = max(models, key=models.get) if models else None
    return ids, matrix, model


def make_run_id(scope: dict[str, Any], pca_dims: int, umap_dims: int, eps: float, min_samples: int) -> str:
    raw = json.dumps(
        {"scope": scope, "pca": pca_dims, "umap": umap_dims, "eps": eps, "min_samples": min_samples, "at": now()},
        sort_keys=True,
    )
    return "sem-" + hashlib.sha256(raw.encode()).hexdigest()[:12]


def cluster(
    db: Path,
    identity: str | None,
    conversation_type: str | None,
    pca_dims: int,
    umap_dims: int,
    eps: float,
    min_samples: int,
    neighbors: int,
    seed: int,
) -> str:
    np, PCA, DBSCAN, umap = imports()
    ids, x, embedding_model = load_conversation_vectors(db, identity, conversation_type)
    n_samples, n_features = x.shape
    if n_samples < 3:
        raise SystemExit("Need at least 3 conversations to cluster.")

    actual_pca = max(2, min(pca_dims, n_features, n_samples - 1))
    actual_umap = max(2, min(umap_dims, actual_pca, n_samples - 2))
    actual_neighbors = max(2, min(neighbors, n_samples - 1))

    print(f"loaded {n_samples} conversations x {n_features} embedding dimensions", flush=True)
    print(f"PCA -> {actual_pca} dimensions", flush=True)
    pca = PCA(n_components=actual_pca, random_state=seed)
    x_pca = pca.fit_transform(x)
    explained = float(pca.explained_variance_ratio_.sum())
    print(f"PCA retained {explained:.1%} variance", flush=True)

    print(f"UMAP -> {actual_umap} dimensions (neighbors={actual_neighbors})", flush=True)
    reducer = umap.UMAP(
        n_components=actual_umap,
        n_neighbors=actual_neighbors,
        metric="cosine",
        min_dist=0.05,
        random_state=seed,
    )
    x_umap = reducer.fit_transform(x_pca)

    print(f"DBSCAN eps={eps} min_samples={min_samples}", flush=True)
    labels = DBSCAN(eps=eps, min_samples=min_samples, metric="euclidean").fit_predict(x_umap)

    print("2-D UMAP for visualization only", flush=True)
    vis = umap.UMAP(
        n_components=2,
        n_neighbors=actual_neighbors,
        metric="cosine",
        min_dist=0.05,
        random_state=seed,
    ).fit_transform(x_pca)

    counts: dict[int, int] = defaultdict(int)
    for label in labels.tolist():
        counts[int(label)] += 1
    cluster_count = len([k for k in counts if k >= 0])
    noise_count = counts.get(-1, 0)

    scope = {"identity": identity, "conversation_type": conversation_type}
    run_id = make_run_id(scope, actual_pca, actual_umap, eps, min_samples)
    ensure_cluster_schema(db)
    with connect(db) as con:
        con.execute(
            """INSERT INTO semantic_cluster_runs
               (run_id,created_at,scope_json,embedding_model,sample_count,vector_dimensions,
                pca_dimensions,umap_dimensions,eps,min_samples,cluster_count,noise_count)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                run_id, now(), json.dumps(scope, sort_keys=True), embedding_model,
                n_samples, n_features, actual_pca, actual_umap, eps, min_samples,
                cluster_count, noise_count,
            ),
        )
        for i, cid in enumerate(ids):
            con.execute(
                """INSERT INTO conversation_reductions
                   (run_id,conversation_id,cluster_id,pca_json,umap_json,vis_x,vis_y)
                   VALUES(?,?,?,?,?,?,?)""",
                (
                    run_id, cid, int(labels[i]),
                    json.dumps([float(v) for v in x_pca[i]]),
                    json.dumps([float(v) for v in x_umap[i]]),
                    float(vis[i, 0]), float(vis[i, 1]),
                ),
            )
        for cluster_id, size in sorted(counts.items()):
            con.execute(
                "INSERT INTO semantic_clusters(run_id,cluster_id,size) VALUES(?,?,?)",
                (run_id, cluster_id, size),
            )

    print(f"run {run_id}: {cluster_count} clusters, {noise_count} noise points", flush=True)
    for cluster_id, size in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        name = "noise" if cluster_id == -1 else f"cluster {cluster_id}"
        print(f"  {name:12} {size}")
    return run_id


def show_status(db: Path) -> None:
    ensure_cluster_schema(db)
    with connect(db) as con:
        rows = con.execute(
            """SELECT run_id,created_at,scope_json,sample_count,pca_dimensions,umap_dimensions,
                      eps,min_samples,cluster_count,noise_count
               FROM semantic_cluster_runs ORDER BY created_at DESC LIMIT 20"""
        ).fetchall()
    if not rows:
        print("no semantic clustering runs")
        return
    for row in rows:
        print(
            f"{row['run_id']} samples={row['sample_count']} clusters={row['cluster_count']} "
            f"noise={row['noise_count']} pca={row['pca_dimensions']} umap={row['umap_dimensions']} "
            f"eps={row['eps']} min_samples={row['min_samples']} scope={row['scope_json']}"
        )


def export_csv(db: Path, run_id: str, output: Path) -> None:
    ensure_cluster_schema(db)
    with connect(db) as con:
        rows = con.execute(
            """SELECT r.conversation_id,c.title,COALESCE(i.identity,'') AS identity,
                      COALESCE(o.conversation_type,'') AS conversation_type,
                      COALESCE(o.summary,'') AS summary,r.cluster_id,r.vis_x,r.vis_y
               FROM conversation_reductions r
               JOIN conversations c USING(conversation_id)
               LEFT JOIN identity_classifications i USING(conversation_id)
               LEFT JOIN conversation_organizations o USING(conversation_id)
               WHERE r.run_id=? ORDER BY r.cluster_id,c.title""",
            (run_id,),
        ).fetchall()
    if not rows:
        raise SystemExit(f"No rows found for run {run_id}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["conversation_id","title","identity","conversation_type","summary","cluster_id","umap_x","umap_y"])
        for row in rows:
            writer.writerow([row[k] for k in row.keys()])
    print(f"wrote {len(rows)} rows to {output}")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run")
    run.add_argument("--db", type=Path, default=DB_DEFAULT)
    run.add_argument("--identity", choices=["LAKOTA","BROOKE","SHARED","UNKNOWN"])
    run.add_argument("--type", dest="conversation_type")
    run.add_argument("--pca-dims", type=int, default=50)
    run.add_argument("--umap-dims", type=int, default=10)
    run.add_argument("--eps", type=float, default=0.8)
    run.add_argument("--min-samples", type=int, default=5)
    run.add_argument("--neighbors", type=int, default=15)
    run.add_argument("--seed", type=int, default=42)

    status = sub.add_parser("status")
    status.add_argument("--db", type=Path, default=DB_DEFAULT)

    export = sub.add_parser("export")
    export.add_argument("run_id")
    export.add_argument("output", type=Path)
    export.add_argument("--db", type=Path, default=DB_DEFAULT)

    args = parser.parse_args()
    if args.command == "run":
        cluster(
            args.db, args.identity, args.conversation_type,
            args.pca_dims, args.umap_dims, args.eps, args.min_samples,
            args.neighbors, args.seed,
        )
        return 0
    if args.command == "status":
        show_status(args.db)
        return 0
    export_csv(args.db, args.run_id, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
