# Runtime Validator Matrix

Execution profile: `markdown-script-mvp-v1`

This MVP persists one creator-facing Markdown DramaScript revision. It does not claim to produce the full rc2.4 artifact bundle.

| Validator | Origin | Required Artifacts | Markdown Profile | Reason |
| --- | --- | --- | --- | --- |
| runtime_script_revision_structure | runtime_policy | creator_facing_markdown_script | APPLICABLE | Validates the persisted Markdown revision shape. |
| genericity | migrated_skill | skill_package | APPLICABLE | Validates package genericity using package-contained forbidden terms. |
| schema | migrated_skill | drama_script_json, beat_registry, coverage_report, assumption_log, conflict_registry, source_claim_audit, handoff, creator_presentation, test_reports | NOT_APPLICABLE | Requires the full rc2.4 artifact bundle; markdown-script-mvp-v1 stores only Markdown. |
| source_claim_audit | migrated_skill | drama_script_json, beat_registry, coverage_report, assumption_log, conflict_registry, source_claim_audit, handoff, creator_presentation, test_reports | NOT_APPLICABLE | Requires source-claim-audit and related bundle artifacts. |
| assumptions_and_extensions | migrated_skill | drama_script_json, beat_registry, coverage_report, assumption_log, conflict_registry, source_claim_audit, handoff, creator_presentation, test_reports | NOT_APPLICABLE | Requires assumption/extension bundle artifacts. |
| handoff_contract | migrated_skill | drama_script_json, beat_registry, coverage_report, assumption_log, conflict_registry, source_claim_audit, handoff, creator_presentation, test_reports | NOT_APPLICABLE | Requires handoff manifest and bundle refs. |
| creator_presentation | migrated_skill | drama_script_json, beat_registry, coverage_report, assumption_log, conflict_registry, source_claim_audit, handoff, creator_presentation, test_reports | NOT_APPLICABLE | Requires creator presentation bundle artifact. |
| coverage_evidence | migrated_skill | drama_script_json, beat_registry, coverage_report, assumption_log, conflict_registry, source_claim_audit, handoff, creator_presentation, test_reports | NOT_APPLICABLE | Requires coverage reports and beat evidence. |
| artifact_integrity | migrated_skill | drama_script_json, beat_registry, coverage_report, assumption_log, conflict_registry, source_claim_audit, handoff, creator_presentation, test_reports | NOT_APPLICABLE | Requires the full artifact registry/hash bundle. |
| core_story_beats | migrated_skill | drama_script_json, beat_registry, coverage_report, assumption_log, conflict_registry, source_claim_audit, handoff, creator_presentation, test_reports | NOT_APPLICABLE | Requires core-story-beat registry and coverage artifacts. |
| markdown_json_equivalence | migrated_skill | drama_script_json, beat_registry, coverage_report, assumption_log, conflict_registry, source_claim_audit, handoff, creator_presentation, test_reports | NOT_APPLICABLE | Requires both Markdown and JSON script artifacts. |

Approval blocks only on applicable required validators. For this profile, `runtime_script_revision_structure` is required and must be `PASS`.
