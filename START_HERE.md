# START HERE

This is the master tutorial. Follow it in order for a new project.

## Stage 0 — Create the project copy

Create a new repository from this template, then clone it:

```bash
git clone <YOUR-REPO-URL>
cd <YOUR-REPO>
chmod +x scripts/check.sh
```

Confirm the starting state:

```bash
git status
./scripts/preflight.sh
```

Do not write app code yet.

## Stage 1 — Discuss the idea

Open `prompts/01-discuss-idea.md` and paste it into your chosen AI chat.

Discuss the project until the important unknowns are resolved. Then fill:

- `docs/00_IDEA.md`
- `docs/01_PROJECT_BRIEF.md`
- `docs/02_REQUIREMENTS.md`

Use `prompts/02-fill-planning-docs.md` to have the AI generate clean replacement content for those templates.

## Stage 2 — Design the app

Discuss the technical design before broad implementation.

Fill:

- `docs/03_ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `docs/TESTING.md`

Decide the stack, major modules, data flow, storage/API choices, and what will prove the app works.

## Stage 3 — Build the roadmap

Use `prompts/03-create-build-plan.md`.

Fill:

- `docs/04_BUILD_PLAN.md`
- `TASKS.md`

Break v0.1 into small tasks. Prefer slices that leave the app runnable or testable. A task must have one outcome, acceptance criteria, likely files, verification steps, and dependencies.

## Stage 4 — Start exactly one task

Choose the next legal task from `TASKS.md` and copy only that task into `docs/ACTIVE_TASK.md`.

Create a branch:

```bash
git switch main
git pull --ff-only
git switch -c build/BUILD-001-short-name
```

Use `edit/`, `fix/`, or `chore/` instead for those task types.

Check your state:

```bash
git status
```

## Stage 5 — Ask the AI for one small slice

Open `prompts/04-write-small-slice.md`.

Give the AI:

- `docs/ACTIVE_TASK.md`
- only the architecture/context needed for this task
- the existing source files it must understand
- any relevant errors

Ask for the smallest coherent implementation. If the task is still too large, split it into checkpoints such as `BUILD-001A`, `BUILD-001B`, and `BUILD-001C`.

Paste generated code only into the exact repo paths identified by the response. Do not create `final`, `fixed`, `new`, or backup copies beside real source files.

## Stage 6 — Check the work

Inspect changes first:

```bash
git status
git diff
```

Run the project checks:

```bash
./scripts/check.sh
```

If a check fails, use `prompts/06-debug-failure.md`. Give the AI the exact error and only the relevant code/context.

After two materially different failed repair approaches, stop and reassess the root cause instead of continuing random edits.

## Stage 7 — Review and understand

When checks pass, use `prompts/05-review-code.md` with the diff and relevant files.

The review should check correctness, scope, duplication, architecture fit, regressions, security concerns, and acceptance criteria. It should also explain the code in plain language so you understand what you are accepting.

Make only necessary fixes, then rerun:

```bash
./scripts/check.sh
git diff
```

## Stage 8 — Commit, push, and open a PR

Stage only intended files:

```bash
git add <file1> <file2>
git diff --cached
```

Commit:

```bash
git commit -m "build: add <capability>"
```

Push:

```bash
git push -u origin HEAD
```

Create a pull request:

```bash
gh pr create
```

Review the PR diff before merging.

## Stage 9 — Finish the checkpoint

After the PR is merged:

```bash
git switch main
git pull --ff-only
```

Update:

- task status in `TASKS.md`
- `docs/CURRENT_STATE.md`
- `docs/AI_HANDOFF.md`
- `docs/DECISIONS.md` if a durable decision changed
- `docs/BUGS.md` if an unresolved bug was discovered
- `docs/CHANGELOG.md` for user-visible changes

Then delete the local merged branch when you are ready:

```bash
git branch -d <branch-name>
```

Return to Stage 4 for the next task.

## Stage 10 — Release

When all tasks for the target release are complete, follow `docs/RELEASE_CHECKLIST.md`. Run full checks, review unresolved bugs, verify setup instructions, and create the release intentionally.

## The loop to remember

```text
pick one task
→ branch
→ fill ACTIVE_TASK
→ ask AI for a tiny slice
→ paste code
→ diff
→ checks
→ debug if needed
→ AI review + explanation
→ checks again
→ stage
→ commit
→ push
→ PR
→ merge
→ update project state
→ next task
```
