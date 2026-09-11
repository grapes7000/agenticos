# Git Tutorial for One Task

Use this sequence for each task.

## 1. Start from current main

```bash
git switch main
git pull --ff-only
git status
```

## 2. Create a task branch

Examples:

```bash
git switch -c build/BUILD-001-settings-screen
git switch -c edit/EDIT-001-button-label
git switch -c fix/FIX-001-crash-on-start
git switch -c chore/CHORE-001-update-packaging
```

## 3. Inspect changes while working

```bash
git status
git diff
```

`git status` tells you which files changed. `git diff` shows the unstaged content changes.

## 4. Stage only intended files

Prefer explicit paths:

```bash
git add app/path/to/file.py docs/CURRENT_STATE.md
git diff --cached
```

Review `git diff --cached` carefully. This is what the commit will contain.

## 5. Commit

```bash
git commit -m "build: add settings screen"
```

Useful prefixes:

- `build:` new capability
- `edit:` small behavior/UI change
- `fix:` bug repair
- `chore:` tooling/docs/maintenance
- `test:` test-only work
- `docs:` documentation-only work

## 6. Push the branch

```bash
git push -u origin HEAD
```

After the first push, later pushes can usually use:

```bash
git push
```

## 7. Create a PR

```bash
gh pr create
```

Before merging, inspect the PR diff and verify checks.

## 8. After merge

```bash
git switch main
git pull --ff-only
```

When you are sure the branch was merged:

```bash
git branch -d <branch-name>
```

## Commands to avoid casually

Do not use these just because an AI suggests them:

```text
git reset --hard
git clean -fd
git push --force
```

They can destroy or rewrite work. Understand the situation first.
