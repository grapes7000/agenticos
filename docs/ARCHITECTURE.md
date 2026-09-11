# AgenticOS architecture

## Supported core

The supported core has five layers:

1. `settings.py` resolves paths and local service configuration.
2. `database.py` owns the AgenticOS SQLite schema and migrations.
3. `workflows.py` gathers read-only status and produces maintenance advice.
4. `dashboard.py` renders the same structured status as HTML.
5. `cli.py` exposes these capabilities through one stable command tree.

Every supported command should return or render structured data. Human reports
and the dashboard are views of that data, not separate sources of truth.

## Safety model

- Inspection is read-only by default.
- Maintenance commands produce proposals, never automatic deletions.
- Commands use argument arrays rather than shell interpolation.
- Private exports, databases, logs, and generated reports never belong in Git.
- Optional external tools are detected and reported without making them hard
  dependencies.

## Compatibility layer

The older scripts remain callable from `agentos legacy <command>`. Selected
well-known commands such as `health`, `security`, and `openclaw-prep` are also
forwarded directly. New features should be added to `agenticos/`, not by adding
another shell wrapper.

## Data ownership

The supported AgenticOS database is `settings.database_path`. The default is
`~/.local/share/agenticos/agentos.sqlite3`. The ChatGPT memory archive keeps a
separate database because it has different provenance and privacy requirements.
The CLI discovers the existing archive under `chatgpt-memory/data` unless a
different path is configured.
