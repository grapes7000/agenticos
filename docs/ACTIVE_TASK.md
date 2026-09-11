# Active Task

## CHATGPT-MEMORY-3.5–3.8 — Deep-memory consolidation and integration

**Area:** ChatGPT memory pipeline

**Status:** IMPLEMENTED — awaiting local regression run before real full extraction

## Completed scope

### 3.5 — Deduplication, temporal state, conflicts, review

Implemented in `chatgpt-memory/src/deep_memory_finalize.py`:

- conservative duplicate grouping over immutable atomic `knowledge_items`;
- no deletion/rewrite of source-backed evidence during consolidation;
- effective temporal status with explicit user override support;
- deterministic `supersedes` links only when explicit current versus
  historical/superseded evidence exists;
- potential current-state contradictions stored in `knowledge_conflicts`;
- ambiguous conflicts and blocked candidates added to `knowledge_review_queue`;
- durable corrections stored in `knowledge_overrides`;
- suppression and forced-status overrides affect generated consolidation views,
  not the original atomic facts.

### 3.6 — Project and semantic-cluster consolidation

Implemented:

- canonical `knowledge_groups` and `knowledge_group_members`;
- per-project/per-namespace consolidation only;
- source evidence from every grouped member retained;
- latest global semantic cluster membership/labels attached as context;
- cluster context contributes to project snapshots but never establishes truth;
- `project_memory_snapshots` stores rebuildable current state, decisions,
  configuration, errors/fixes, workflows, history, conflicts, and cluster
  context.

### 3.7 — Markdown and search integration

Implemented:

- generated project views under `chatgpt-memory/memory/<namespace>/projects/`;
- `README.md`, `CURRENT_STATE.md`, `DECISIONS.md`, `CONFIGURATION.md`,
  `ERRORS_AND_FIXES.md`, `WORKFLOWS.md`, `HISTORY.md`, and `CONFLICTS.md`;
- source references use `chatgpt://conversation/...` provenance identifiers;
- `tools/search_memory.py` now loads consolidated durable groups by default;
- durable knowledge receives retrieval priority for real keyword matches;
- raw ChatGPT chunks, attachments, and Obsidian remain available for semantic
  recall and source inspection;
- `--durable` can restrict search to consolidated durable knowledge.

### 3.8 — Main pipeline integration

Implemented:

- `chatgpt-memory/src/run_stage3.py` runs/resumes the complete Stage-3 sequence;
- it builds/reuses the queue, processes bounded LLM batches, writes atomic
  knowledge, links relations, and runs finalization/rendering;
- repeated runs reuse completed unchanged passages;
- the runner stops if multiple batches make no queue progress rather than
  spinning forever;
- `bin/agentos-chatgpt-pipeline` now invokes Stage 3 after Stage-2B clustering;
- `agentos-chatgpt-pipeline status` exposes deep queue and snapshot state.

## Canonical Stage-3 tables

```text
deep_memory_runs
deep_memory_extractions
deep_memory_candidates
knowledge_items
knowledge_item_projects
knowledge_evidence
knowledge_relations
knowledge_groups
knowledge_group_members
knowledge_conflicts
knowledge_review_queue
knowledge_overrides
project_memory_snapshots
```

## Regression tests

Run locally:

```bash
python3 -m unittest \
  chatgpt-memory/tests/test_deep_memory_stage3.py \
  chatgpt-memory/tests/test_deep_memory_queue.py \
  chatgpt-memory/tests/test_deep_memory_finalize.py \
  chatgpt-memory/tests/test_durable_search.py -v
```

The new tests cover duplicate grouping, semantic-cluster context, state
conflicts, supersession, durable overrides, snapshots/Markdown rendering, and
durable search in addition to the 3.1–3.4 tests.

## Review boundary

Do not redesign Stage 3 before the regression suite passes locally. Once it
passes, run the real pipeline through tmux and inspect early extraction batches,
blocked candidates, open conflicts, and rendered project memory before treating
the generated durable memory as trusted day-to-day context.
