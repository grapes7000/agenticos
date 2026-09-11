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
  `${XDG_CONFIG_HOME:-~/.config}/agenticos/config.toml`.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for component boundaries and
[docs/CHATGPT_MEMORY_PLAN.md](docs/CHATGPT_MEMORY_PLAN.md) for the project and
error knowledge model.

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

The large historical `.venv` is not required by the new core. Optional legacy
AI workflows may still need Ollama and their original Python packages.
