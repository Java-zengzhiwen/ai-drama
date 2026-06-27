# Migration Remediation Report

## Review Conclusion

Previous review result was `PASS_WITH_REQUIRED_FIXES`. This remediation fixes the confirmed blockers without remigration.

## Structure Change

Before remediation, active files were split across top-level `skills/`, `contracts/`, `validators/`, and `fixtures/`.

After remediation, the active rc2.4 Skill package is self-contained:

- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/SKILL.md`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/references/`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/templates/`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/schemas/`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/contracts/`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/`

Top-level `contracts/`, `validators/`, and `fixtures/` no longer carry pseudo-shared active content.

## Neutral-project Investigation

SOURCE_ROOT contains rc2.4 `fixtures/neutral-project` and `test-reports/neutral-project`.

Evidence found:

- `script-handoff-manifest.json` has `handoff_status=pending_user_review`.
- `presentation.md` does not contain `formal_integration_status=hold`.
- Current rc2.4 validators require `pending_script_approval` or `script_approved_downstream_unauthorized`, and require formal integration hold in creator presentation.
- `pre-review-gate-v0.6.1-rc2.4` passes for a chapter candidate/pre-review gate, not for neutral-project.

No separate trustworthy active rc2.4 neutral fixture was found.

## Fixture Final Status

`neutral-project` is `STALE_INCONSISTENT_REFERENCE_ONLY`.

It was moved to:

`reference/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/stale-fixtures/neutral-project/`

No fixture business fields were edited.

## Expected Reports Final Status

Expected reports moved with the stale fixture and are no longer active expected baselines.

Known mismatches:

| validator | expected result | actual result | error code | evidence |
|---|---|---|---|---|
| `validate_handoff_contract.py` | pass | fail | `ERR_HANDOFF_STATE` | `/tmp` validator run during review |
| `validate_artifact_integrity.py` | pass | fail | `ERR_FORMAL_INTEGRATION_STATUS` | review-confirmed mismatch |
| `validate_creator_presentation.py` | pass | fail | `ERR_PRESENTATION_FORMAL_INTEGRATION` | `/tmp` validator run during review |
| `validate_schema.py` | pass | not executed as baseline | `SCHEMA_RUNTIME_NOT_EXECUTED_DEPENDENCY_MISSING` | `jsonschema` not installed |

## Historical Reference Cleanup

The rc2.3 phase-b report was moved to:

`reference/historical/ai-drama-script-adaptation-skill/v0.6.1-rc2.3-phase-b/phase-b-implementation-report.md`

It is not used as rc2.4 current-state evidence.

## rc2.4 Pre-Review Gate

`reference/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/reports/pre-review-gate-v0.6.1-rc2.4.md` is retained as reference evidence. It proves a rc2.4 pre-review gate/check set for a chapter candidate, not the neutral fixture.

## Unresolved Issues

- No active business fixture baseline exists yet.
- Storyboard Design, Storyboard QC, and Shot Prompt active packages remain unresolved.
- `jsonschema` is not installed in this environment.

## Decisions

- Migration Remediation Verdict: `PASS`
- Baseline Commit Decision: `ALLOW_COMMIT`
- Batch 1 Decision: `ALLOW_BATCH_1`
