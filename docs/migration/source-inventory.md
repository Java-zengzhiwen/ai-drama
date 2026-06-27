# Source Inventory

Preflight source root: `/Users/zengzhiwen/AI-manju/ai-drama-script-agent-lab`

## Candidate Skills

| capability | source_path | skill_id | declared_version | current_form | selected_or_rejected | decision_reason |
|---|---|---|---|---|---|---|
| Script Adaptation | `04-work/ai-drama-script-adaptation-skill-v0.6.1-rc2.4/SKILL.md` | `ai-drama-script-adaptation-skill-v0.6.1-rc2.4` | `v0.6.1-rc2.4` | CODEX_SKILL | selected | Current rc2.4 candidate has SKILL.md, schemas, validators, contracts, fixtures, test reports, and runtime-only notes. |
| Script QC / Rubric | `04-work/ai-drama-script-adaptation-skill-v0.6.1-rc2.4/references/coverage-qc-rubric.md` plus validators | `ai-drama-script-adaptation-skill-v0.6.1-rc2.4` | `v0.6.1-rc2.4` | VALIDATOR | selected | QC is embedded in the script adaptation package through coverage/source/equivalence/handoff validators. |
| Storyboard Design | not found as active Skill in allowed SOURCE_ROOT discovery | unknown | null | UNKNOWN | UNRESOLVED | No `SKILL.md` or active non-report package found for storyboard design. |
| Storyboard QC | not found as active Skill in allowed SOURCE_ROOT discovery | unknown | null | UNKNOWN | UNRESOLVED | No independent Storyboard QC Skill found. |
| Shot Prompt | not found as active Skill in allowed SOURCE_ROOT discovery | unknown | null | UNKNOWN | UNRESOLVED | No active Shot Prompt Skill found; visual/image prompt outputs were excluded. |

## Duplicate Candidates

- rc2.3 phase-b, rc2.3 r1/r2/r3, and rc2.4 script adaptation candidates exist under `04-work/`.
- rc2.4 selected because README/CHANGELOG describe isolated runtime reproduction support and current rc2.4 fixes, while preserving runtime-only package boundaries.
- `05-live-reproduction/*/runtime` directories duplicate runtime material as reproduction outputs; kept out of active migration to avoid generated reproduction copies.

## Contracts

- JSON Schemas: `hybrid-script.schema.json`, `core-story-beats.schema.json`, `core-story-beat-coverage.schema.json`.
- Presentation contracts: `script-approval-creator-presentation-contract-v2.md`, `script-revision-presentation-contract-v2.md`.

## Validators

- Copied executable Python validators from rc2.4 `validators/`.
- Invocation evidence is in copied reference tests. The old neutral-project expected reports are stale reference material, not active baseline evidence.

## Fixture

- `fixtures/neutral-project` was found in the rc2.4 source package, but current rc2.4 validators reject its handoff/presentation state while expected reports claim pass.
- It was demoted to `reference/.../stale-fixtures/neutral-project/`.
- No active business fixture baseline is selected.
- Excluded pilot/conflict-free extra fixture sets to keep one baseline.
