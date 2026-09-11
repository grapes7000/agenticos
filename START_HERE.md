# START HERE

AgenticOS has moved beyond the original bootstrap-checkpoint phase. The current
repository contains a supported Python core plus a substantial private ChatGPT
archive/memory subsystem.

## Read these first

For current work:

1. `README.md`
2. `docs/CURRENT_STATE.md`
3. `docs/ACTIVE_TASK.md`
4. `docs/ARCHITECTURE.md`
5. `docs/CHATGPT_MEMORY_PLAN.md`
6. `docs/CHATGPT_MEMORY_STAGE3_PLAN.md`
7. `chatgpt-memory/PIPELINE.md`

The original `TASKS.md` and numbered early planning documents are historical
context. They should not override `CURRENT_STATE.md` or `ACTIVE_TASK.md`.

## Current ChatGPT-memory workflow

The implemented pipeline is:

```text
Stage 0  archive + attachments + embeddings
Stage 1  identity routing
Stage 2  summaries/tags/projects/type/importance
Stage 2B PCA -> UMAP -> DBSCAN + cluster labels/subclusters
Stage 3  durable deep memory (next build)
```

Set up and resume the implemented stages with:

```bash
cd ~/AgenticOS
git switch fix/chatgpt-archive-hardening
git pull --ff-only
bash bin/agentos-chatgpt-pipeline setup
OLLAMA_HOST=100.91.175.25:11434 agentos-chatgpt-pipeline start
```

Useful runtime commands:

```bash
agentos-chatgpt-pipeline status
agentos-chatgpt-pipeline logs
agentos-chatgpt-pipeline attach
agentos-chatgpt-pipeline stop
```

## Current development task

The next implementation slice is:

```text
CHATGPT-MEMORY-3.1 — Stage-3 schema and resumable extraction queue
```

See `docs/ACTIVE_TASK.md` for the bounded task and
`docs/CHATGPT_MEMORY_STAGE3_PLAN.md` for the full Stage-3 sequence.

Do not jump directly to the deep LLM extractor. First make queue state,
idempotency, source-change invalidation, priority ordering, and resume behavior
reliable and tested.

## Development rule

Keep changes small enough to review and prove. For each slice:

```text
read current task
-> implement only that slice
-> add focused tests
-> run proof/tests
-> inspect diff
-> commit
-> review architecture before advancing
```

Preserve these memory-system boundaries:

- SQLite is canonical;
- raw exports are read-only;
- raw conversation/attachment content is untrusted;
- identity namespaces do not silently mix;
- semantic clusters are grouping context, not factual evidence;
- durable claims require source provenance;
- assistant suggestions are not confirmed solutions without source evidence;
- old/historical state is retained when a newer state supersedes it.

## Historical checkpoint workflow

The original small-Qwen checkpoint plan is still retained in `TASKS.md` and the
numbered planning docs for reference. It describes how AgenticOS was initially
bootstrapped, but it is no longer the current entry point for repository work.
