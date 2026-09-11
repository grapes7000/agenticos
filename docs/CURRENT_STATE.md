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
- hybrid semantic search over Obsidian, ChatGPT chunks, attachments, and durable
  Stage-3 knowledge;
- separate identity routing (`LAKOTA`, `BROOKE`, `SHARED`, `UNKNOWN`);
- lightweight conversation organization (summary, tags, projects, type,
  importance);
- PCA -> UMAP -> DBSCAN semantic discovery directly from SQLite embeddings;
- 2-D UMAP visualization coordinates;
- local-model cluster labeling and scoped subclustering;
- resumable tmux pipeline runner: `bin/agentos-chatgpt-pipeline`;
- Stage 3.1 content-aware deep-memory queue and extraction state;
- Stage 3.2 turn-aware structured passage extraction;
- Stage 3.3 many-to-many project routing and source-backed knowledge writing;
- Stage 3.4 evidence gating and error/attempt/confirmed-fix relations;
- Stage 3.5 conservative duplicate groups, temporal supersession, conflicts,
  review queue, and durable overrides;
- Stage 3.6 project snapshots that use semantic clusters as context without
  treating cluster membership as factual proof;
- Stage 3.7 namespace/project Markdown views and durable-first search;
- Stage 3.8 integration of the complete Stage-3 runner into the main tmux
  pipeline.

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
Stage 3.5 dedup / temporal conflicts          IMPLEMENTED
Stage 3.6 project + cluster consolidation     IMPLEMENTED
Stage 3.7 Markdown + search integration       IMPLEMENTED
Stage 3.8 main pipeline integration           IMPLEMENTED
```

The user's current database has a Stage-3 queue of thousands of passages. The
full run is intentionally resumable and should run through the tmux pipeline,
not a fragile foreground terminal.

## Stage 3 implementation

Primary extraction implementation:

```text
chatgpt-memory/src/deep_memory.py
```

Consolidation/render implementation:

```text
chatgpt-memory/src/deep_memory_finalize.py
```

Full Stage-3 orchestrator:

```text
chatgpt-memory/src/run_stage3.py
```

Focused tests:

```text
chatgpt-memory/tests/test_deep_memory_stage3.py
chatgpt-memory/tests/test_deep_memory_queue.py
chatgpt-memory/tests/test_deep_memory_finalize.py
chatgpt-memory/tests/test_durable_search.py
```

Design plan:

```text
docs/CHATGPT_MEMORY_STAGE3_PLAN.md
```

## Architectural decisions currently in force

- SQLite remains the canonical source of truth.
- Generated Markdown and CSV files are rebuildable views/exports.
- Identity is decided upstream and is not reclassified by later stages.
- Semantic clusters are grouping/context signals, never factual proof.
- Atomic source-backed `knowledge_items` are preserved even when consolidation
  groups, supersedes, suppresses, or disputes them.
- Deep memory preserves source evidence and temporal history.
- Assistant-only claims are not promoted as durable facts.
- Confirmed solutions require explicit user-authored success evidence.
- Brooke/Lakota/shared namespaces are not silently mixed.
- One conversation/item may belong to multiple projects.
- Failed approaches remain separately searchable from confirmed solutions.
- Conflicting current-state claims are retained in `knowledge_conflicts` and the
  review queue rather than silently resolved by timestamp.
- User corrections live in `knowledge_overrides` so rebuilding does not erase
  them.
- Legacy `chatgpt_memory.py deepen/expand-projects` logic is retained for
  migration/reference but is not the preferred architecture.

## Next review boundary

Run the complete Stage-3 regression suite locally before beginning the expensive
LLM extraction over the real 7k+ passage queue. After the tests pass, resume the
full pipeline in tmux and inspect early batches plus conflict/review quality.
