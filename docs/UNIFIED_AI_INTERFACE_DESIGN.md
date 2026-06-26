# Unified AI Workflow Interface Design

> **Status:** Design + implementation blueprint  
> **Date:** 2026-06-26  
> **Audience:** READ-ME for Lakota + AI-LEARN for future AgenticOS agents

## Goal

Build one integrated workflow management interface for AgenticOS that lets Lakota interact with OpenWebUI, Hermes, OpenClaw, AgenticOS agents, and future local/remote agents from a single consistent command center.

The interface should:

1. Standardize how tools talk to each other.
2. Detect what Lakota is working on.
3. Prompt Lakota with useful check-ins and suggested next actions.
4. Automate safe task sequences across agents.
5. Keep strong logs for performance, failures, and optimization suggestions.
6. Preserve AgenticOS security rules: private-by-default, local/Tailscale access, no raw secrets in prompts/logs.

## Product Name

Working name: **AgenticOS Unified AI Console**

Other possible names:

- **Command Nest**
- **AgenticOS Copilot Hub**
- **Workflow Brain**
- **Unified Agent Console**

## Core UX

The interface has five main panes:

| Pane | Purpose |
|---|---|
| **Now** | Shows what AgenticOS thinks Lakota is working on right now. |
| **Ask / Prompt** | A unified prompt box that can route to Hermes, OpenWebUI, OpenClaw, or an AgenticOS workflow. |
| **Suggestions** | AI-generated helpful next actions, ranked by safety and usefulness. |
| **Workflows** | One-click task sequences such as “summarize project”, “run health check”, “prep OpenClaw context”, “make safe git checkpoint”. |
| **Logs / Optimizer** | Recent agent runs, latency, errors, repeated pain points, and suggested improvements. |

## Primary User Flow

1. Lakota opens the AgenticOS console.
2. Console checks context sources:
   - recent OpenWebUI chats, if available and explicitly allowed
   - recent Hermes/Telegram task history, via summaries/logs
   - active project directories from allowlisted locations
   - recent git changes in `/home/lakota/AgenticOS` or other allowlisted workspaces
   - recent Obsidian AgenticOS notes
   - currently running Docker services
3. Console displays:
   - “Looks like you’re working on: `<topic>`”
   - “Useful next actions:”
   - “Want me to help with any of these?”
4. Lakota can accept one, edit it, ask a new question, or say “not that.”
5. The interface routes the task through the correct protocol adapter.
6. Each step logs what happened, how long it took, whether it succeeded, and what could be improved.

## Context Detection

### Sources

| Source | Method | Safety rule |
|---|---|---|
| OpenWebUI chats | Read chat DB/export through an adapter | Read-only, redacts secrets, user-controlled toggle |
| Hermes | Read summaries / scheduled outputs / current task handoff | Do not scrape raw private chats unless explicitly allowed |
| OpenClaw | Read sandbox context/output dirs | Restrict to AgenticOS sandbox path |
| AgenticOS agents | Read latest AI-LEARN/READ-ME notes + JSON logs | Prefer structured latest notes over old timestamp piles |
| Directories | Watch/list allowed project directories | Only allow configured roots, default no secret paths |
| Git | `git status`, recent commit messages, changed files | Never stage/commit secrets; respect `.gitignore` |
| Docker | `docker ps`, health, labels, compose files | No env value dumping |
| Obsidian | Read AgenticOS vault notes | Prefer `AI-LEARN` and `READ-ME` notes |

### Working Context Model

Every context scan should produce this normalized shape:

```json
{
  "detected_focus": "AgenticOS unified AI console",
  "confidence": 0.82,
  "evidence": [
    {"source": "git", "summary": "docs and dashboard changed in AgenticOS"},
    {"source": "openwebui", "summary": "recent chats mention agents and workflow UI"},
    {"source": "obsidian", "summary": "latest AI-LEARN notes mention note policy and OpenWebUI knowledge"}
  ],
  "risks": ["OpenWebUI chat reading requires explicit opt-in"],
  "suggested_questions": [
    "Are you designing the UI or ready to implement it?",
    "Should this be local-only or reachable through Tailscale?"
  ]
}
```

## Unified Communication Protocol

All agents/tools should accept the same envelope. Adapters translate the envelope into each tool’s native command/API.

```json
{
  "task_id": "uuid",
  "created_at": "iso-8601",
  "requested_by": "lakota",
  "source_ui": "agenticos-console",
  "intent": "design|code|research|operate|debug|summarize|ask",
  "target": "hermes|openwebui|openclaw|agenticos|docker|obsidian|git",
  "safety_level": "read_only|dry_run|write_local|service_restart|external_publish",
  "prompt": "human request here",
  "context_refs": [
    {"type": "file", "path": "/home/lakota/AgenticOS/docs/..."},
    {"type": "note", "path": "/home/lakota/vault/Agentic OS/..."}
  ],
  "constraints": {
    "no_raw_secrets": true,
    "tailscale_only": true,
    "dry_run_default": true
  },
  "expected_outputs": ["markdown_summary", "git_diff", "log_record"],
  "requires_confirmation": false
}
```

## Protocol Adapters

### Hermes Adapter

Use for:

- system operations
- file edits
- git work
- Docker inspection
- scheduled reminders
- multi-step agentic tasks

Interface:

```bash
agentos route hermes --task data/tasks/<task_id>.json
```

Or via Telegram/Hermes gateway for interactive prompts.

### OpenWebUI Adapter

Use for:

- local model Q&A
- knowledge-base retrieval
- lightweight brainstorming
- model comparison

Capabilities:

- Read recent chats after opt-in.
- Send prompt to selected local model.
- Attach AgenticOS knowledge collection.
- Return answer + model metadata + latency.

Safety:

- Never read/write OpenWebUI DB directly without an adapter and explicit read/write mode.
- Redact tokens/API keys from chat exports.

### OpenClaw Adapter

Use for:

- coding agent tasks
- sandboxed project experiments
- implementation planning

Capabilities:

- Prepare context pack.
- Write task prompt into `openclaw-sandbox/input/`.
- Run OpenClaw only inside configured sandbox/project.
- Collect results from `openclaw-sandbox/output/`.

### AgenticOS Agent Adapter

Use for:

- daily briefings
- health checks
- security summaries
- memory search
- file butler dry-runs
- bug hunts
- build quality checks

Example commands:

```bash
agentos briefing
agentos health
agentos security-summary
agentos build-quality
agentos memory
agentos openclaw-prep
```

### Git Adapter

Use for:

- status summaries
- checkpoint commits
- diff review
- branch planning

Safety:

- Always check `.gitignore` first.
- Scan staged changes for secret patterns before commit.
- Prefer local commits before remote pushes.

## Task Sequence Automation

### Workflow: “What am I working on?”

1. Scan active allowed directories.
2. Check git status for changed files.
3. Read latest AgenticOS AI-LEARN notes.
4. Optionally read OpenWebUI chat summaries.
5. Rank likely work topics.
6. Prompt Lakota:

```text
Looks like you’re working on AgenticOS unified agent workflow design.
Want help with one of these?
1. Turn the design into a working dashboard prototype.
2. Add OpenWebUI chat summarizer adapter.
3. Add logging database schema and CLI.
4. Make a git checkpoint.
```

### Workflow: “Help me continue”

1. Identify latest task list / git changes / latest handoff.
2. Create or update task plan.
3. Suggest 3 safe next actions.
4. Ask one concise question only if needed.
5. Execute accepted action.
6. Log outcome.

### Workflow: “Safe implementation”

1. Create plan.
2. Run read-only checks.
3. Implement minimal change.
4. Run tests.
5. Scan for secrets.
6. Commit locally.
7. Summarize exact files changed.

### Workflow: “Optimize AgenticOS”

1. Query run logs for slow/failing/repeated workflows.
2. Find repeated errors or manual steps.
3. Suggest automation candidates.
4. Rank by impact and safety.
5. Offer one-click implementation plan.

## Prompting Behavior

The unified AI should be proactive but not annoying.

### Check-in Prompt Template

```text
I think you’re working on: {detected_focus}
Confidence: {confidence}

I can help by:
1. {safe_task_1}
2. {safe_task_2}
3. {safe_task_3}

Want me to do one, adjust the list, or stay quiet?
```

### Suggestion Rules

Suggestions must be:

- relevant to current context
- safe by default
- concrete and actionable
- no more than 3 at a time
- labeled by risk level
- easy to decline

Example:

```text
Suggested next actions:

[Safe/read-only] Review latest git diff and summarize what changed.
[Safe/local write] Create a design doc for the unified console.
[Needs confirmation] Restart Homepage after dashboard config changes.
```

## Logging and Optimization

### Log Store

Use SQLite for structured logs:

```text
/home/lakota/AgenticOS/data/db/agent_os.sqlite
```

Add these tables if missing:

```sql
CREATE TABLE IF NOT EXISTS unified_tasks (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  source_ui TEXT NOT NULL,
  intent TEXT NOT NULL,
  target TEXT NOT NULL,
  safety_level TEXT NOT NULL,
  status TEXT NOT NULL,
  prompt_redacted TEXT NOT NULL,
  detected_focus TEXT,
  confidence REAL,
  duration_ms INTEGER,
  error_redacted TEXT
);

CREATE TABLE IF NOT EXISTS unified_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id TEXT NOT NULL,
  ts TEXT NOT NULL,
  event_type TEXT NOT NULL,
  source TEXT NOT NULL,
  message_redacted TEXT NOT NULL,
  duration_ms INTEGER,
  metadata_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS unified_suggestions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  detected_focus TEXT NOT NULL,
  suggestion TEXT NOT NULL,
  risk_level TEXT NOT NULL,
  accepted INTEGER DEFAULT 0,
  dismissed INTEGER DEFAULT 0,
  outcome TEXT
);
```

### Metrics to Track

| Metric | Why it matters |
|---|---|
| task duration | Find slow workflows |
| failed commands | Find brittle adapters |
| repeated user corrections | Improve prompts and defaults |
| accepted suggestions | Learn what is useful |
| dismissed suggestions | Reduce annoying prompts |
| manual repeated sequences | Identify automation opportunities |
| model latency/cost/local model used | Choose best model/tool |

### Optimization Suggestions

Every day or week, AgenticOS should generate:

```text
READ-ME: AgenticOS Workflow Optimization Suggestions
```

With sections:

- repeated manual actions
- slowest workflows
- most common failures
- highest-value automations
- stale docs/agents to update
- suggested safe git checkpoints

## UI Layout Wireframe

```text
┌────────────────────────────────────────────────────────────────┐
│ AgenticOS Unified AI Console                                    │
│ Focus: AgenticOS unified interface design        Confidence 82% │
├───────────────────────────┬────────────────────────────────────┤
│ NOW                       │ ASK / ROUTE                         │
│ - Current project         │ [ What do you want to do?        ]  │
│ - Recent git changes      │ Target: Auto ▾  Safety: Dry-run ▾   │
│ - Active services         │ [Run] [Plan] [Ask first]            │
├───────────────────────────┼────────────────────────────────────┤
│ SUGGESTIONS               │ WORKFLOWS                           │
│ 1. Make git checkpoint    │ [Continue work] [Health check]      │
│ 2. Draft implementation   │ [OpenClaw prep] [OpenWebUI summary] │
│ 3. Review errors          │ [Security summary] [Daily briefing] │
├───────────────────────────┴────────────────────────────────────┤
│ LOGS + OPTIMIZER                                                │
│ Last run: health check 2m ago | 3 warnings | Suggest: fix X     │
└────────────────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Local Static Prototype

Files:

- `dashboard/unified-ai-console.html`
- `docs/UNIFIED_AI_INTERFACE_DESIGN.md`

Purpose:

- Nail the UX.
- Make the workflow visible.
- Keep it safe and static.

### Phase 2: Local AgenticOS API

Add:

- `tools/unified_context.py`
- `tools/unified_logger.py`
- `tools/unified_router.py`
- `bin/agentos-unified`

Endpoints/commands:

```bash
agentos-unified context
agentos-unified suggest
agentos-unified route --target hermes --prompt "..."
agentos-unified logs
agentos-unified optimize
```

### Phase 3: Context Connectors

Add read-only connectors:

- OpenWebUI chat summary connector
- Hermes handoff/current task connector
- OpenClaw sandbox connector
- git status connector
- Obsidian latest note connector
- Docker health connector

### Phase 4: Interactive Routing

Add execution path:

- confirmation gates by safety level
- task queue
- status streaming
- retry policy
- result cards

### Phase 5: Learning Optimizer

Add:

- weekly optimization report
- suggestion scoring
- accepted/dismissed feedback
- workflow templates generated from repeated sequences

## Safety Requirements

1. No raw secrets in prompts, logs, notes, commits, or UI.
2. OpenWebUI chat reading is opt-in and redacted.
3. Directory scanning limited to configured allowlist.
4. Service restarts and destructive edits require confirmation.
5. Git commits are local unless Lakota explicitly asks to push.
6. Default mode is read-only or dry-run.
7. Tailscale/local access only unless explicitly changed.

## First Build Recommendation

Start with:

1. Static dashboard prototype.
2. Context detector CLI that reads only:
   - git status
   - latest AgenticOS notes
   - Docker health summary
   - configured directory list
3. Suggestion engine with three safe suggestions.
4. SQLite logger.
5. Local git checkpoint after each working increment.

This gives immediate usefulness without touching risky OpenWebUI internals or exposing secrets.
