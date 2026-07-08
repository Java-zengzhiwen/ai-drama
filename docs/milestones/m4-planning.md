# M4 Planning

M4 must not start implementation until explicitly authorized. Real Agnes
requests remain forbidden unless the user sends:

```text
AUTHORIZE_REAL_AGNES_VIDEO_SMOKE_TEST
```

## Recommendation

Recommended default:

```text
M4 End-to-End Chapter Production Rehearsal
```

Why: the current environment is not ready for a real Agnes smoke test. A mock
provider rehearsal improves production quality without requiring public HTTPS
asset hosting or real provider spend.

Recommended priority:

1. Option B: End-to-End Chapter Production Rehearsal
2. Option C: Generation Result Review / Rerun Quality Workflow
3. Option A: Real Provider Smoke Test + Operations Hardening

## Option A: Real Provider Smoke Test + Operations Hardening

### Goal

Run one minimal real Agnes video smoke test and harden operator checks around
real provider configuration.

### Why Now

This validates the last untested external boundary after M3, but only after
the environment is ready.

### Scope

- Verify `AI_DRAMA_RUNTIME_PROVIDER=agnes`.
- Verify provider-reachable HTTPS `AI_DRAMA_PUBLIC_BASE_URL`.
- Verify Agnes API key status through `LocalSecretStore`.
- Dry-run signed asset delivery.
- After explicit authorization, submit one minimal real video job.
- Record provider job ID, polling outcome, local result persistence, and cleanup notes.

### Non-Scope

- No batch real provider run.
- No production episode export.
- No LibTV, subtitles, BGM, timeline, or post-production.
- No cloud provisioning automation.

### Required Inputs

- Public HTTPS application URL reachable by Agnes.
- Agnes API key configured in `LocalSecretStore`.
- One ready shot with usable image assets.
- Explicit token: `AUTHORIZE_REAL_AGNES_VIDEO_SMOKE_TEST`.

### Success Criteria

- One authorized real Agnes job submits successfully.
- Provider status/result path uses explicit video methods.
- Result bytes persist locally.
- Result content endpoint serves stored bytes.
- No secrets appear in logs, docs, object metadata, or git.

### Risks

- Public asset URL may be unreachable by Agnes.
- Provider may rate-limit or return transient errors.
- Real provider behavior may differ from current documentation.
- Real request may spend credits.

### Test/Verifier Plan

- Keep default tests mocked.
- Add opt-in smoke command only after authorization.
- Re-run `tools/verify_m3_agnes_generation.py`.
- Add a real-smoke report artifact outside git or with redacted metadata only.

### Estimated Implementation Files

- `docs/milestones/m3-baseline-summary.md`
- `docs/m3-real-provider-readiness.md`
- Optional future script: `tools/verify_m3_real_agnes_smoke.py`

## Option B: End-to-End Chapter Production Rehearsal

### Goal

Use one realistic chapter sample under the mock provider to run the complete
production path:

```text
source material
-> shot prompt ready
-> generation queue
-> poller
-> local result persistence
-> result selection
-> review
-> rerun
-> version history
-> operator report
```

### Why Now

It exercises the full M1/M2/M3 workflow without needing real Agnes requests.
This should catch workflow gaps before any real provider or M4 acceptance work.

### Scope

- Build a deterministic rehearsal fixture.
- Create or reuse source material.
- Generate and approve script/storyboard/shot prompts under existing mock path.
- Mark selected shots ready.
- Queue generation jobs.
- Run poller cycles.
- Persist local results.
- Select current result.
- Record review decision.
- Create rerun and preserve prior job/result.
- Emit a rehearsal report.

### Non-Scope

- No real Agnes request.
- No final episode export.
- No LibTV execution.
- No post-production features.
- No new provider abstraction.

### Required Inputs

- One representative chapter fixture.
- Existing mock generation backend.
- Existing M1/M2/M3 services and APIs.
- Existing object store and SQLite runtime.

### Success Criteria

- One command generates a complete rehearsal report.
- All key states are traceable.
- Failure, rerun, and result selection have records.
- Frontend can display version history and current adopted result.
- Rehearsal data does not pollute real production material.

### Risks

- Fixture may become too large.
- Rehearsal may duplicate existing verifier logic.
- UI assertions can become brittle if over-specified.

### Test/Verifier Plan

- Add verifier:

```text
tools/verify_m4_chapter_rehearsal.py
```

- Success token:

```text
M4_CHAPTER_REHEARSAL_PASS
```

- Keep tests deterministic and fake-provider only.
- Reuse existing M1/M2/M3 verifiers for regression.

### Estimated Implementation Files

- `tools/verify_m4_chapter_rehearsal.py`
- `tests/web/test_m4_chapter_rehearsal.py`
- `docs/superpowers/plans/2026-07-05-m4-real-chapter-mvp-acceptance.md`
- Optional fixture under `tests/fixtures/`

## Option C: Generation Result Review / Rerun Quality Workflow

### Goal

Improve the operator workflow around result review, failure categorization,
rerun comparison, and selected result confidence.

### Why Now

M3 provides the mechanics. Operators now need clearer quality traceability
before scaling to larger chapter rehearsals.

### Scope

- Strengthen result review states.
- Improve failure category reporting.
- Compare source job, rerun job, and selected result.
- Add operator-facing quality report.
- Keep prior result/job retention visible.

### Non-Scope

- No new provider.
- No real Agnes request requirement.
- No video editing or timeline.
- No automated aesthetic scoring.

### Required Inputs

- Existing generation result records.
- Existing review records.
- Existing rerun links.
- Mock provider result fixtures.

### Success Criteria

- Operator can explain why a result was selected or rerun.
- Rerun source and overrides are visible and auditable.
- Failed results retain useful category and note metadata.
- Version history remains intact.

### Risks

- Could drift into product-design scope.
- Could overbuild review taxonomy.
- Could duplicate M3 UI if not kept small.

### Test/Verifier Plan

- Extend Web unit tests for review/rerun display.
- Add service/store tests for review metadata integrity if needed.
- Re-run M3 verifier.

### Estimated Implementation Files

- `web/src/features/generation/GenerationResultsTab.tsx`
- `web/src/features/generation/GenerationResultsTab.test.tsx`
- `ai_drama_web/routers/generation.py`
- `tests/web/test_generation_api.py`

## Default M4 Proposal

Default M4 should be:

```text
M4 End-to-End Chapter Production Rehearsal
```

It does not require real Agnes requests and should add one command:

```bash
python3 tools/verify_m4_chapter_rehearsal.py
```

Expected success output:

```text
M4_CHAPTER_REHEARSAL_PASS
```
