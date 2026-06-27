# Migration Report

## Goal

Create a clean, traceable Skill Runtime Migration Baseline for the first MVP vertical chain without developing runtime code.

## Actual Scope

The active migration scope is the confirmed rc2.4 Script Adaptation package and its embedded Script QC validators/rubrics. The active package is self-contained under `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/`.

Storyboard Design, Storyboard QC, and Shot Prompt remain unresolved because no trustworthy active Skill package was found in SOURCE_ROOT discovery.

## Counts

- Active Skills: 1
- Active Schema files: 3
- Active Contract files: 2
- Active Validator files: 11
- Active Fixture files: 0
- Stale fixture/reference files: 33
- Other reference-only files: 5

## External Dependencies

- EXTERNAL_DEPENDENCY: `jsonschema>=4.23.0` is declared in the copied `requirements.txt`; no dependency was installed.

## Fixture Status

`neutral-project` is retained only as `STALE_INCONSISTENT` reference material under `reference/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/stale-fixtures/neutral-project/`.

## Unresolved Items

- No trusted active business fixture baseline exists yet.
- Storyboard Design active Skill not found.
- Storyboard QC active Skill not found.
- Shot Prompt active Skill not found.

## Rollback

All migrated and generated support files are listed in `migration/migration-manifest.json`, except the manifest itself. No SOURCE_ROOT files were edited.

## Next Batch 1 Recommendation

Define Skill Package Contract + Skill Registry only. Batch 1 can proceed because it does not require executing business generation or business validators.
