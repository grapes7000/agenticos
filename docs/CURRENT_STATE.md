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
- source-backed project/knowledge index foundation in `knowledge_index.py`;
- Stage 3.1 content-aware deep-memory queue and extraction state;
- Stage 3.2 turn-aware structured passage extraction;
- Stage 3.3 many-to-many project routing and source-backed knowledge writing;
- Stage 3.4 evidence gating and error/attempt/confirmed-fix relations.

Current pipeline boundary:

```text
Stage 0  import / attachments / embeddings     DONE
Stage 1  identity routing                     DONE
Stage 2  lightweight organization             DONE
Stage 2B semantic clustering / refinement     DONE
Stage 3.1 schema + resumable queue             IMPLEMENTED
Stage 3.2 structured passage extraction       IMPLEMENTED
Stage 3.3 project routing + knowledge writer  IMPLEMENTED
Stage 3.4 relations / confirmed fixes         IMPLEMENTED
Stage 3.5 dedup / temporal conflicts          NOT STARTED
```

The user's current database may still be processing earlier implemented stages;
the code paths are resumable and existing completed work is reused.

## Stage 3 implementation

Primary implementation:

```text
chatgpt-memory/src/deep_memory.py
```

CLI wrapper:

```text
bin/agentos-chatgpt-deep-memory
```

Focused tests:

```text
chatgpt-memory/tests/test_deep_memory_stage3.py
```

Design plan:

```text
docs/CHATGPT_MEMORY_STAGE3_PLAN.md
```

Stage 3 is intentionally not integrated into the main pipeline runner yet;
that remains Stage 3.8 after the deep-memory stages are stable.

## Architectural decisions currently in force

- SQLite remains the canonical source of truth.
- Generated Markdown and CSV files are rebuildable views/exports.
- Identity is decided upstream and is not reclassified by later stages.
- Semantic clusters are context for grouping/consolidation, not factual proof.
- Deep memory preserves source evidence and temporal history.
- Assistant-only claims are not promoted as durable facts.
- Confirmed solutions require explicit user-authored success evidence.
- Brooke/Lakota/shared namespaces are not silently mixed.
- One conversation/item may belong to multiple projects.
- Failed approaches remain separately searchable from confirmed solutions.
- Legacy `chatgpt_memory.py deepen/expand-projects` logic is retained for
  migration/reference but is not the preferred architecture for new Stage-3
  work.

## Next review boundary

Stop after Stage 3.4. Run the local Stage-3 tests and review queue invalidation,
passage provenance, project routing, solution-confirmation rules, and relation
quality before beginning Stage 3.5.
