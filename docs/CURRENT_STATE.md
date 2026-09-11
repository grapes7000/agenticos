# Current State

## Current focus

AgenticOS is past the original CLI-bootstrap planning state. The supported CLI,
compatibility commands, local dashboard/status infrastructure, and ChatGPT
archive tooling all exist.

The active development focus on branch `fix/chatgpt-archive-hardening` is the
ChatGPT memory pipeline.

## ChatGPT memory status

Implemented:

- incremental ChatGPT archive import from ZIP or extracted directories;
- conversation change detection and selective invalidation;
- conversation and attachment semantic embeddings;
- attachment MIME recovery, SHA deduplication, extraction, and provenance;
- hybrid semantic search over Obsidian, ChatGPT chunks, and attachments;
- separate identity routing (`LAKOTA`, `BROOKE`, `SHARED`, `UNKNOWN`);
- lightweight conversation organization (summary, tags, projects, type,
  importance);
- PCA -> UMAP -> DBSCAN semantic discovery directly from SQLite embeddings;
- 2-D UMAP visualization coordinates;
- local-model cluster labeling;
- scoped subclustering for oversized Stage-2 categories;
- resumable tmux pipeline runner: `bin/agentos-chatgpt-pipeline`;
- source-backed project/knowledge index foundation in `knowledge_index.py`.

Current pipeline boundary:

```text
Stage 0  import / attachments / embeddings     DONE
Stage 1  identity routing                     DONE
Stage 2  lightweight organization             DONE
Stage 2B semantic clustering / refinement     DONE
Stage 3  durable deep memory                  PLANNED
```

The user's current database may still be processing the implemented stages; the
code path itself is present and resumable.

## Active work

Design and implement Stage 3 deep memory. The plan is:

```text
docs/CHATGPT_MEMORY_STAGE3_PLAN.md
```

The first implementation slice is **3.1 — schema and resumable extraction
queue**. Deep extraction should not begin until queue state, invalidation, and
idempotency are tested.

## Architectural decisions currently in force

- SQLite remains the canonical source of truth.
- Generated Markdown and CSV files are rebuildable views/exports.
- Identity is decided upstream and is not reclassified by later stages.
- Semantic clusters are context for grouping/consolidation, not factual proof.
- Deep memory must preserve source evidence and temporal history.
- Confirmed solutions require explicit success evidence from the source.
- Brooke/Lakota/shared namespaces must not be silently mixed.
- Legacy `chatgpt_memory.py deepen/expand-projects` logic is retained for
  migration/reference but is not the preferred architecture for new Stage-3
  work.

## Next review boundary

After Stage 3.1 (schema + queue) is implemented with tests, review the schema and
resume/invalidation behavior before building the LLM passage extractor in Stage
3.2.
