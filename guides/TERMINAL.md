# Terminal Tutorial

These are the routine terminal checks for the guided workflow.

## Before starting work

```bash
pwd
git status
./scripts/preflight.sh
```

Confirm you are in the correct repo and understand the current Git state.

## While editing

```bash
git status
git diff
```

Use these often. They show what changed before you commit anything.

## After pasting AI-generated code

Run:

```bash
./scripts/check.sh
```

Then run any task-specific commands listed in `docs/ACTIVE_TASK.md`.

Examples may include:

```bash
pytest
npm test
npm run lint
npm run typecheck
npm run build
cargo test
go test ./...
```

Only run commands appropriate for the project's actual stack.

## When something fails

Keep the exact command and exact output. Do not summarize away the important error text before asking an AI for debugging help.

Use `prompts/06-debug-failure.md` and provide:

- command run;
- complete relevant error;
- active task;
- relevant code/files.

## Before committing

```bash
./scripts/check.sh
git status
git diff
```

Then stage specific files and inspect the staged diff:

```bash
git add <paths>
git diff --cached
```

## Important habit

A green command is evidence. An AI saying "this should work" is not evidence. Keep terminal output as the source of truth for what was actually verified.
