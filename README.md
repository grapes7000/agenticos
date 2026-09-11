# AgenticOS

AgenticOS is a local-first personal AI control center. It provides one command
for inspecting this machine, searching project knowledge, reviewing safe
maintenance suggestions, and opening a small local dashboard. It is not an
operating system and it does not make destructive changes automatically.

## Everyday commands

```bash
./bin/agentos status
./bin/agentos doctor
./bin/agentos audit
./bin/agentos maintain
./bin/agentos dashboard
./bin/agentos memory search "display error"
./bin/agentos memory projects
./bin/agentos memory errors --project AgenticOS
```

`status` is the best starting point. It gives a short human-readable overview.
`audit` gathers more detailed read-only evidence. `maintain` only suggests
actions; it does not apply them.

## ChatGPT memory pipeline

The private ChatGPT archive pipeline is staged and resumable:

```text
archive/attachments/embeddings
-> identity routing
-> lightweight organization
-> PCA/UMAP/DBSCAN semantic discovery
-> durable deep memory (Stage 3, planned)
```

For the implemented Stages 0–2B:

```bash
bash bin/agentos-chatgpt-pipeline setup
OLLAMA_HOST=100.91.175.25:11434 agentos-chatgpt-pipeline start
agentos-chatgpt-pipeline status
```

See:

- [chatgpt-memory/PIPELINE.md](chatgpt-memory/PIPELINE.md) for the runnable
  pipeline;
- [docs/CHATGPT_MEMORY_PLAN.md](docs/CHATGPT_MEMORY_PLAN.md) for the overall
  memory architecture;
- [docs/CHATGPT_MEMORY_STAGE3_PLAN.md](docs/CHATGPT_MEMORY_STAGE3_PLAN.md) for
  the deep-memory implementation plan.

## Design

- `agenticos/` contains the supported CLI, settings, database, workflows, and
  dashboard renderer.
- `agents/`, `tools/`, and `scripts/` contain older specialist workflows. They
  remain available through compatibility CLI commands while they are gradually
  folded into the supported core.
- `chatgpt-memory/` contains the private, local ChatGPT archive pipeline. Raw
  exports, generated views, and databases are ignored by Git.
- Runtime data defaults to `${XDG_DATA_HOME:-~/.local/share}/agenticos`.
- Configuration defaults to
  `${XDG_CONFIG_HOME:-~/.config/agenticos/config.toml`.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for component boundaries.

## Configuration

Copy `config/config.example.toml` to `~/.config/agenticos/config.toml` and edit
only what differs on this machine. Environment variables with the `AGENTOS_`
prefix override the file.

## Development

AgenticOS supports Python 3.11 or newer and has no required third-party runtime
dependencies for its core CLI.

```bash
python3 -m unittest discover -s tests -v
python3 -m agenticos.cli doctor
```

The large historical `.venv` is not required by the supported core. The ChatGPT
semantic clustering pipeline installs its optional NumPy/scikit-learn/UMAP
dependencies into a dedicated virtual environment via
`agentos-chatgpt-pipeline setup`. Other legacy AI workflows may still require
Ollama and their original Python packages.
