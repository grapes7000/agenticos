# AI Chat Rules

These rules apply whenever an AI is helping with this repository, including ChatGPT, Ollama chat, Claude chat, or a coding assistant.

## Authority order

1. Latest explicit user instruction.
2. `docs/ACTIVE_TASK.md`.
3. This file.
4. Approved project docs and decisions.
5. Existing code patterns.

## Before writing code

- Read `docs/ACTIVE_TASK.md`.
- Read only the project docs and source files needed for that task.
- Inspect existing implementation before proposing replacements.
- Keep the context narrow; do not request the whole repo without a reason.
- For a non-trivial change, give a short plan first.

## One-task rule

Work on exactly one BUILD, EDIT, FIX, or CHORE task at a time.

Do not choose the next task, mark tasks DONE, expand the roadmap, or silently change product/architecture decisions. The human controls task lifecycle and Git.

If a task is too large for one safe implementation response, propose named checkpoints such as `BUILD-003A`, `BUILD-003B`, and `BUILD-003C`.

## Implementation rules

- Prefer minimal targeted changes over broad rewrites.
- Preserve unrelated working behavior.
- Reuse existing utilities/components/conventions where appropriate.
- Do not create `final`, `final2`, `fixed`, `new`, `backup`, or parallel source implementations.
- Do not add dependencies, change APIs/storage/auth/security/deployment, or redesign architecture unless the active task explicitly requires it.
- Do not leave abandoned commented-out code or dead implementations.
- Do not disable tests/type checks/security controls to make checks pass.
- Never expose or commit secrets.
- Do not access outside the repository or use `sudo` unless explicitly authorized.

## Code delivery format for chat models

For each proposed change, provide:

1. exact repository path;
2. `NEW FILE`, `COMPLETE REPLACEMENT`, or `TARGETED EDIT`;
3. code/content to paste;
4. short explanation of what it does;
5. exact check/test commands the human should run.

Never claim a command was run unless the user supplied its output or the AI actually has tool access and ran it.

## Debugging

1. Start from the exact failure/output.
2. Identify the likely root cause.
3. Apply the smallest repair.
4. Rerun the original failing command.
5. Run relevant regression checks.

After two materially different failed approaches, stop and reassess assumptions/root cause rather than continuing speculative edits.

## Verification and review

Before a task is accepted:

- inspect `git diff`;
- run relevant tests/checks;
- run `./scripts/check.sh`;
- compare results against every acceptance criterion;
- have the change reviewed when practical;
- explain important code so the human understands what is being accepted.

## Git safety

The human controls Git lifecycle. An AI may explain commands, but must not assume permission to push, merge, force-push, rewrite history, delete branches, reset hard, or clean files.

The standard task flow is branch -> edit -> diff -> check -> review -> stage -> commit -> push -> PR -> merge -> update state.

## Documentation

Update durable docs only when relevant:

- `docs/CURRENT_STATE.md` — what works now and what comes next.
- `docs/AI_HANDOFF.md` — context another chat/agent needs.
- `docs/DECISIONS.md` — durable product/architecture decisions.
- `docs/BUGS.md` — unresolved known defects.
- `docs/CHANGELOG.md` — user-visible changes.

Do not turn documentation into a transcript.

## Completion report

At the end of a task report:

- Task
- Changed
- Files
- Checks run/results
- Acceptance criteria status
- Remaining concerns/unverified items
- Suggested Git next step

Then stop. Do not begin the next task automatically.
