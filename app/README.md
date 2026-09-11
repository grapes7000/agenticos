# App Workspace

This directory is intentionally almost empty in the starter.

Do **not** choose a framework just because the template has an `app/` folder. Pick the stack during the architecture stage, then create the real application here (or deliberately choose another source directory and update the project docs).

## Before adding code

Complete:

- `docs/00_IDEA.md`
- `docs/01_PROJECT_BRIEF.md`
- `docs/02_REQUIREMENTS.md`
- `docs/03_ARCHITECTURE.md`
- `docs/04_BUILD_PLAN.md`
- `TASKS.md`
- `docs/ACTIVE_TASK.md`

Then implement only the first active slice.

## Optional placeholder-file pattern

If it helps your manual copy/paste workflow, you may create an empty source file with only a comment such as:

```text
# BUILD-001 implementation goes below this line.
```

or the equivalent comment syntax for the chosen language.

When the AI returns real code, replace the placeholder with the actual implementation. Do not keep parallel `final`, `fixed`, `new`, or backup copies.

## Where should generated code go?

The AI response should always state:

```text
PATH: exact/repo/path
ACTION: NEW FILE | COMPLETE REPLACEMENT | TARGETED EDIT
```

Paste code only into that intended path, then run the checks listed in `docs/ACTIVE_TASK.md` and `./scripts/check.sh`.
