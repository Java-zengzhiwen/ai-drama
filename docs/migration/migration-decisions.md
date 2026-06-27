# Migration Decisions

## Active Package

- Script Adaptation Skill rc2.4 is kept as the only active Skill package.
- The active package is self-contained under `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/`.
- `schemas/`, `contracts/`, and `validators/` now live inside the Skill version directory because no second active Skill currently shares them.

## Reference Only

- `reference/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/tests/` keeps test invocation evidence only.
- `reference/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/reports/pre-review-gate-v0.6.1-rc2.4.md` is rc2.4 reference evidence for a chapter candidate/pre-review gate, not proof that `neutral-project` is valid.
- `reference/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/stale-fixtures/neutral-project/` keeps the stale neutral fixture and its expected reports as reference-only evidence.
- `reference/historical/ai-drama-script-adaptation-skill/v0.6.1-rc2.3-phase-b/phase-b-implementation-report.md` is historical rc2.3 phase-b evidence only.

## Excluded

- `.deps`, `vendor`, `__pycache__`, cache directories, release ZIPs, reproduction outputs, media, visual preapproval, bible-stage, image prompt, scene stabilization, LibTV, downstream execution outputs.
- Extra fixtures `pilot-shengsi` and `conflict-free-project`.
- Active Storyboard Design, Storyboard QC, and Shot Prompt packages because no trustworthy active Skill package was found in SOURCE_ROOT.

## Fixture Decision

- No active business fixture baseline is present after remediation.
- `neutral-project` is `STALE_INCONSISTENT` because current rc2.4 validators reject its handoff/presentation/artifact integration state while its expected reports still claim pass.
- The stale fixture was not edited to make tests pass.

## Mapping

Machine-readable per-file mapping lives in `migration/migration-manifest.json`.
