# Release Checklist

## Scope
- [ ] All tasks planned for this release are DONE or intentionally deferred.
- [ ] Deferred work is recorded.
- [ ] No unrelated work was silently added.

## Quality
- [ ] `./scripts/check.sh` passes.
- [ ] Full relevant test suite passes.
- [ ] Build/package step succeeds when applicable.
- [ ] Known bugs are reviewed in `docs/BUGS.md`.

## Product
- [ ] Core user flows work from a clean start.
- [ ] Setup instructions are accurate.
- [ ] Error states are understandable.
- [ ] UI resizing/accessibility checks are complete when relevant.

## Security / data
- [ ] No secrets are committed.
- [ ] Sensitive data handling matches the architecture.
- [ ] Dependency/security concerns are reviewed when relevant.

## Documentation
- [ ] `README.md` describes how to run the app.
- [ ] `docs/CURRENT_STATE.md` is current.
- [ ] `docs/AI_HANDOFF.md` is current.
- [ ] `docs/CHANGELOG.md` contains user-visible changes.
- [ ] Important decisions are in `docs/DECISIONS.md`.

## Git / release
- [ ] Final diff is reviewed.
- [ ] Release branch/PR is clean.
- [ ] Version/tag strategy is decided.
- [ ] Release notes are prepared.
