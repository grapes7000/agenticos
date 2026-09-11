# ChatGPT Memory Pipeline

`bin/agentos-chatgpt-pipeline` wraps the archive, semantic-discovery, and durable-memory workflow into one resumable command.

## Full pipeline

The runner now implements the complete path:

1. optional archive import + chat/attachment embeddings (`--source PATH`);
2. identity routing (`LAKOTA`, `BROOKE`, `SHARED`, `UNKNOWN`);
3. lightweight organization (summary, tags, projects, conversation type, importance);
4. global semantic discovery from conversation embeddings:
   - normalize and mean-pool chunk embeddings;
   - PCA;
   - higher-dimensional UMAP;
   - DBSCAN;
   - separate 2-D UMAP for visualization/export only;
5. local-LLM cluster labels;
6. semantic subclustering of oversized Stage-2 categories;
7. Stage-3 deep-memory queue + passage extraction;
8. source-backed project/knowledge writing and error/fix relations;
9. conservative duplicate grouping, temporal supersession, conflicts, review queue, and durable overrides;
10. project + semantic-cluster consolidation into `project_memory_snapshots`;
11. generated per-namespace project Markdown views;
12. durable-first hybrid memory search.

The pipeline is resumable. Completed unchanged Stage-3 passages are reused, just as earlier identity/organization work is reused.

## One-time setup

```bash
cd ~/AgenticOS
git switch fix/chatgpt-archive-hardening
git pull --rebase
bash bin/agentos-chatgpt-pipeline setup
```

This creates `~/.venv-chatgpt-pipeline`, installs clustering dependencies, makes the runner commands executable, and symlinks them into `~/.local/bin`.

## Resume the current database

```bash
OLLAMA_HOST=100.91.175.25:11434 agentos-chatgpt-pipeline start
```

`start` launches a detached tmux session named `chatgpt-pipeline`.

```bash
agentos-chatgpt-pipeline attach
agentos-chatgpt-pipeline logs
agentos-chatgpt-pipeline status
agentos-chatgpt-pipeline stop
```

The current database already has a Stage-3 queue. Running the pipeline resumes it; it does not create duplicate passage rows.

## Start from a fresh export

```bash
OLLAMA_HOST=100.91.175.25:11434 \
agentos-chatgpt-pipeline start \
  --source /path/to/chatgpt-export
```

## Stage-3 standalone runner

To run only Stage 3 against an already prepared database:

```bash
OLLAMA_HOST=100.91.175.25:11434 \
python3 chatgpt-memory/src/run_stage3.py \
  --model qwen2.5:7b-instruct \
  --host 100.91.175.25:11434
```

The standalone low-level commands remain available through `deep_memory.py` for inspection/recovery.

## Canonical output

SQLite remains canonical:

```text
chatgpt-memory/data/memory.sqlite3
```

Important Stage-3 tables:

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

Semantic CSV maps:

```text
chatgpt-memory/data/semantic-exports/
```

Generated durable project views:

```text
chatgpt-memory/memory/
  lakota/projects/<project>/
  brooke/projects/<project>/
  shared/projects/<project>/
  unknown/projects/<project>/
```

Generated Markdown is a rebuildable view. Do not edit it as the canonical memory source; corrections belong in SQLite overrides/review decisions.

## Durable search

`agentos-memory-search` now searches consolidated durable groups by default before falling back to raw semantic recall.

```bash
agentos-memory-search "AgenticOS database path"
agentos-memory-search --durable "SSH port"
agentos-memory-search --chatgpt "original troubleshooting conversation"
```

## Safety/quality rules

- source-backed atomic facts are preserved after consolidation;
- assistant-only claims are blocked rather than promoted;
- confirmed solutions require user-authored success evidence;
- identities/namespaces are never silently mixed;
- clusters are context, not factual evidence;
- timestamps alone do not resolve contradictory state;
- explicit current vs historical/superseded evidence may create `supersedes` relations;
- unresolved contradictions remain in `knowledge_conflicts` + review queue;
- user corrections are durable `knowledge_overrides` and survive rebuilds.

See:

- `docs/CHATGPT_MEMORY_STAGE3_PLAN.md`
- `docs/CURRENT_STATE.md`
- `docs/ACTIVE_TASK.md`
- `chatgpt-memory/README.md`
