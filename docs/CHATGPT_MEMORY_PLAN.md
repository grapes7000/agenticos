# ChatGPT project and error memory plan

## Goal

Turn the private ChatGPT export into source-backed project dossiers where:

- one conversation can belong to any number of projects;
- one passage can produce facts for different projects;
- errors, failed approaches, fixes, decisions, configuration, and current state
  are distinct searchable categories;
- every claim points back to its conversation and date;
- uncertainty and historical status are preserved;
- Brooke and shared conversations retain their privacy boundaries.

## Implemented foundation

`knowledge_index.py` adds three non-destructive tables to the existing archive:

- `projects`: canonical project names and aliases;
- `conversation_projects`: a many-to-many routing table with relevance and
  rationale;
- `knowledge_items`: normalized source-backed facts grouped into categories
  such as `error`, `solution`, `decision`, `configuration`, and `status`.

An FTS5 index supports combined keyword, project, and category search. Generated
project folders contain a README, source-conversation list, and one document per
knowledge category.

## Extraction plan

### Phase 1 — deterministic rebuild

Build the index from existing analysis and extracted facts:

```bash
agentos memory reindex
agentos memory projects
agentos memory errors --project agenticos
agentos memory search "database path" --project agenticos
```

This phase is resumable and makes no model calls.

### Phase 2 — reroute all conversations

The earlier import marked 400 of 563 conversations as `UNKNOWN`. That identity
classification must not prevent project routing. Run a local-model topic pass
over every conversation, while keeping identity/privacy classification separate.

For each 8–12k-character passage, return:

```json
{
  "projects": [
    {"name": "AgenticOS", "relevance": 0.91, "evidence": "..."},
    {"name": "Local AI Infrastructure", "relevance": 0.63, "evidence": "..."}
  ]
}
```

Merge aliases conservatively (`Agentic OS` and `AgenticOS`) but never combine
projects solely because their names are similar.

### Phase 3 — passage-level knowledge extraction

Extract independent items rather than one summary per conversation:

- `error`: symptom, exact message, affected component, environment;
- `failed_approach`: attempted action and observed failure;
- `solution`: action that the user confirmed worked;
- `decision`: choice and reason;
- `configuration`: paths, services, versions, and settings;
- `status`: current or historical project state;
- `lesson`: reusable conclusion.

Each item receives one primary project and optional related projects. Never turn
an assistant suggestion into a successful solution unless later user text
confirms the outcome.

### Phase 4 — error linking and deduplication

Normalize error signatures while retaining original text. Link:

```text
error -> failed approaches -> confirmed solution -> affected projects -> sources
```

Deduplicate semantically similar errors only when component, symptom, and cause
agree. Preserve separate occurrences as evidence links.

### Phase 5 — review queue

Put low-confidence project assignments, conflicting current-state claims, and
unconfirmed solutions into a small review queue. Corrections should become
durable overrides so future rebuilds do not undo them.

## Quality checks

- Every generated statement has a source conversation ID.
- Every solution has explicit success evidence.
- A conversation can appear in multiple project dossiers.
- Searches can filter by project, category, status, date, and confidence.
- Rebuilding is idempotent.
- Raw conversation content is treated as untrusted input and remains local.
