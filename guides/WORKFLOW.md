# Workflow Overview

This starter uses two phases: **plan the project once**, then **repeat the same small implementation loop**.

## Planning phase

```text
idea
→ project brief
→ requirements
→ architecture
→ testing strategy
→ build plan
→ TASKS.md
```

Do not begin broad implementation while important product or architecture decisions are still unresolved.

## Repeating implementation loop

```text
choose one task
→ create task branch
→ copy task into ACTIVE_TASK.md
→ ask AI for one small slice
→ paste code into exact paths
→ inspect git diff
→ run checks
→ debug only evidenced failures
→ review + understand code
→ rerun checks
→ stage exact files
→ inspect staged diff
→ commit
→ push
→ PR
→ merge
→ update state/handoff
→ next task
```

## Stop conditions

Stop the current task when its acceptance criteria are satisfied. Do not use spare time or context to start adjacent tasks.

If implementation reveals a real new requirement or architectural constraint, record it and deliberately re-plan rather than silently expanding scope.

If two materially different debugging approaches fail, stop making speculative edits and reassess the root cause.

## Human vs AI responsibilities

### Human controls

- repository files;
- terminal commands and observed output;
- task activation/completion;
- Git branches, staging, commits, pushes, PRs, and merges;
- acceptance of AI-generated code.

### AI helps with

- discussing product decisions;
- filling structured templates;
- proposing architecture;
- breaking work into small tasks;
- writing one bounded code slice;
- debugging from real evidence;
- reviewing and explaining the resulting code.

The chat is temporary. The repository documents are durable project state.
