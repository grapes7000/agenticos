# AI Handoff

## Project

AgenticOS is a local-first Python control utility plus a private ChatGPT archive
and memory subsystem. The supported core exposes system inspection/search/status
capabilities; `chatgpt-memory/` owns the separate archive, vector, provenance,
and durable-memory workflow.

## Current state

Implementation is well beyond the original bootstrap checkpoints.

On branch `fix/chatgpt-archive-hardening`, the ChatGPT memory system currently
has:

- incremental archive/attachment ingestion;
- conversation and attachment embeddings;
- hybrid semantic search;
- separate identity routing;
- lightweight conversation organization;
- PCA -> UMAP -> DBSCAN semantic clustering;
- cluster labeling and large-category subclustering;
- a resumable tmux pipeline runner;
- a source-backed project/knowledge index foundation.

The next major task is Stage 3 deep memory. Stage 3 is planned but not yet
implemented in the preferred architecture.

## Architecture that must be preserved

- SQLite is canonical; Markdown/CSV are rebuildable outputs.
- Raw exports remain read-only and raw content is untrusted input.
- Identity routing is upstream and must not be silently changed by later stages.
- Brooke, Lakota, shared, and unknown namespaces stay separate.
- Stage-2 summaries/tags/project hints are organizational metadata, not factual
  evidence.
- Semantic clusters are grouping context, not factual proof.
- Durable claims must point to source conversations/evidence.
- A successful fix requires explicit success evidence, not merely an assistant
  suggestion.
- Historical/superseded facts must be retained rather than overwritten.
- Reruns should be idempotent and source changes should invalidate only affected
  derived state.

## Active task

`CHATGPT-MEMORY-3.1` — Stage-3 schema and resumable extraction queue.

Do not implement the LLM extractor before queue/resume/invalidation behavior is
stable and tested.

## Stage-3 sequence

```text
3.1 schema + queue
3.2 structured passage extractor
3.3 project routing + source-backed knowledge writer
3.4 error/failure/solution relations
3.5 deduplication + temporal state + conflicts
3.6 project/cluster consolidation
3.7 Markdown + search integration
3.8 main pipeline integration
```

## Important files

```text
chatgpt-memory/src/chatgpt_archive.py
chatgpt-memory/src/identify_fast.py
chatgpt-memory/src/organize_fast.py
chatgpt-memory/src/semantic_cluster.py
chatgpt-memory/src/label_semantic_clusters.py
chatgpt-memory/src/knowledge_index.py
bin/agentos-chatgpt-pipeline
```

## Source of truth

Read these before changing the memory pipeline:

- `docs/CURRENT_STATE.md` — current implementation state;
- `docs/ACTIVE_TASK.md` — current bounded task;
- `docs/CHATGPT_MEMORY_PLAN.md` — overall memory architecture;
- `docs/CHATGPT_MEMORY_STAGE3_PLAN.md` — Stage-3 design and slices;
- `chatgpt-memory/PIPELINE.md` — implemented Stages 0–2B runner;
- `chatgpt-memory/README.md` — archive/index/search details;
- `docs/DECISIONS.md` — durable project decisions.

Older checkpoint documents under `docs/00_*` through `docs/04_*` and the
original `TASKS.md` remain useful historical design context but should not be
mistaken for the current active implementation state.
