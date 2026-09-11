# ChatGPT Memory Pipeline

`bin/agentos-chatgpt-pipeline` wraps the archive/memory workflow into one resumable command.

## What it does

1. Optional archive import + chat/attachment embeddings (`--source PATH`)
2. Fast identity routing (`LAKOTA`, `BROOKE`, `SHARED`, `UNKNOWN`)
3. Lightweight organization (summary, tags, projects, conversation type, importance)
4. Global semantic discovery using conversation embeddings:
   - normalize chunk embeddings
   - mean-pool to one vector per conversation
   - PCA
   - UMAP (higher-dimensional clustering representation)
   - DBSCAN
   - separate 2-D UMAP for visualization/export only
5. Local-LLM labels for discovered semantic clusters
6. Automatic semantic subclustering of any Stage-2 category with at least `--large-min` conversations (default 100)
7. CSV exports of global and scoped semantic maps

The pipeline is resumable. It reads the existing SQLite state and skips stages that are already complete. This means the same command can continue a partially processed database or start from a new ChatGPT export.

## One-time setup

```bash
cd ~/AgenticOS
git pull --ff-only
bash bin/agentos-chatgpt-pipeline setup
```

This creates `~/.venv-chatgpt-pipeline`, installs `numpy`, `scikit-learn`, and `umap-learn`, makes the runner executable, and symlinks it into `~/.local/bin`.

## Resume the current database

```bash
OLLAMA_HOST=100.91.175.25:11434 agentos-chatgpt-pipeline start
```

The `start` command launches a detached tmux session named `chatgpt-pipeline`.

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

## Outputs

SQLite remains canonical at:

```text
chatgpt-memory/data/memory.sqlite3
```

Semantic CSV maps are written to:

```text
chatgpt-memory/data/semantic-exports/
```

Clustering runs are retained independently in SQLite, so parameter experiments do not overwrite older runs.
