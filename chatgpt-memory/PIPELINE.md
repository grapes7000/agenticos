# ChatGPT Memory Pipeline

`bin/agentos-chatgpt-pipeline` wraps the implemented archive/memory workflow into
one resumable command.

## Current pipeline boundary

The runner currently implements **Stages 0–2B**:

1. optional archive import + chat/attachment embeddings (`--source PATH`);
2. fast identity routing (`LAKOTA`, `BROOKE`, `SHARED`, `UNKNOWN`);
3. lightweight organization (summary, tags, projects, conversation type,
   importance);
4. global semantic discovery using conversation embeddings:
   - normalize chunk embeddings;
   - mean-pool to one vector per conversation;
   - PCA;
   - UMAP in higher-dimensional clustering space;
   - DBSCAN;
   - separate 2-D UMAP for visualization/export only;
5. local-LLM labels for discovered semantic clusters;
6. automatic semantic subclustering of any Stage-2 category with at least
   `--large-min` conversations (default 100);
7. CSV exports of global and scoped semantic maps.

**Stage 3 deep memory is not yet part of the runner.** Its implementation plan is
in `docs/CHATGPT_MEMORY_STAGE3_PLAN.md`.

The pipeline is resumable. It reads existing SQLite state and skips completed
identity/organization work. Existing semantic clustering runs are reused unless
`--force-clusters` is supplied.

## One-time setup

```bash
cd ~/AgenticOS
git switch fix/chatgpt-archive-hardening
git pull --ff-only
bash bin/agentos-chatgpt-pipeline setup
```

This creates `~/.venv-chatgpt-pipeline`, installs `numpy`, `scikit-learn`, and
`umap-learn`, makes the runner executable, and symlinks it into
`~/.local/bin`.

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

## Start from a fresh export

```bash
OLLAMA_HOST=100.91.175.25:11434 \
agentos-chatgpt-pipeline start \
  --source /path/to/chatgpt-export
```

The same command performs import/indexing first and then resumes later stages.

## Useful options

```text
--model MODEL        Ollama model used for identity/organization/cluster labels
--host HOST          Ollama endpoint
--large-min N        Subcluster categories with at least N conversations (default 100)
--force-clusters     Create new PCA/UMAP/DBSCAN runs instead of reusing existing runs
```

Examples:

```bash
agentos-chatgpt-pipeline start --large-min 75
agentos-chatgpt-pipeline start --force-clusters
agentos-chatgpt-pipeline status
```

## Canonical outputs

SQLite remains canonical at:

```text
chatgpt-memory/data/memory.sqlite3
```

Important implemented tables include:

```text
conversations
chat_chunks
assets
asset_chunks
asset_references
identity_classifications
conversation_organizations
semantic_cluster_runs
conversation_reductions
semantic_clusters
```

Semantic CSV maps are written to:

```text
chatgpt-memory/data/semantic-exports/
```

Clustering runs are retained independently in SQLite, so parameter experiments
do not overwrite older runs.

## What comes next

Stage 3 will consume the outputs above rather than redoing them. It will build
source-backed durable memory for decisions, confirmed fixes, failed approaches,
configuration, project state, workflows, lessons, and temporal state. Semantic
cluster membership will be used as consolidation context, not as factual proof.

See:

- `docs/CHATGPT_MEMORY_PLAN.md` — overall architecture and current status;
- `docs/CHATGPT_MEMORY_STAGE3_PLAN.md` — Stage 3 implementation plan;
- `chatgpt-memory/README.md` — archive/index/search details.
