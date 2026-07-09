# M4.2 Chapter Rehearsal UI Visibility Plan

## Purpose

Plan how to make M4 rehearsal evidence visible inside the existing generation
workspace so an operator can judge chapter production health without opening
the JSON report.

The UI should answer:

- Did the chapter production chain run end to end?
- Which shots succeeded?
- Which shots failed?
- Which shots have reruns?
- Which result is currently adopted?
- Is review complete?
- Is the local video artifact viewable?
- Which real provider items remain deferred?

This is a planning document only. It does not authorize UI implementation,
production code changes, real Agnes requests, or public HTTPS work.

## Current Backend/Report Evidence

M3 and M4 already persist the core production evidence:

- `GET /api/chapters/{chapter_id}/generation/jobs` returns per-shot generation
  jobs with status, attempt number, provider IDs, error code, and timestamps.
- `GET /api/chapters/{chapter_id}/results` returns per-shot result versions,
  current selection, source URL state, local content availability, and local
  content URL.
- `GET /api/generation/jobs/{job_id}` returns the source request for rerun
  comparison.
- `POST /api/results/{result_id}/review` creates review records.
- `POST /api/generation/jobs/{job_id}/rerun` creates a new generation job while
  preserving the original job.
- `tools/verify_m4_chapter_rehearsal.py` writes
  `runtime-data/reports/m4-chapter-rehearsal-report.json` and `.md`.

M4.1 report fields include:

- `schema_version`
- `environment.provider`
- `environment.real_agnes_request_made`
- `scenarios`
- `job_status_timeline`
- `result_versions`
- `current_selection`
- `reviews`
- `failure_categories_tested`
- `local_content_urls`
- `object_ids`
- `operator_checklist`
- `deferred_items`

## Current UI Gap

The current generation UI already exposes generation rows, result versions,
current selection, preview, review actions, and rerun creation. The gap is that
operators must mentally combine several surfaces and the runtime report to
understand rehearsal health.

Current missing or weak areas:

- No chapter-level rehearsal summary.
- No scenario matrix showing source success versus failed-then-rerun success.
- Attempt history is visible only as latest job in Agnes generation and result
  version rows in results.
- Review records are write-only in the current UI; existing reviews are not
  listed back to the operator.
- `object_id`, `schema_version`, `environment`, `operator_checklist`, and
  `deferred_items` are report-only.
- Real provider deferral is documented but not visible in the generation
  workspace.

## Proposed UI Surfaces

### 1. Chapter Rehearsal Summary Card

- What it shows: provider mode, `real_agnes_request_made`, total shots,
  completed shots, failed shots, rerun shots, selected-result coverage, and
  review coverage.
- Why it matters: one card answers whether the rehearsal is usable at chapter
  level.
- Data source: Phase 1 derives counts from existing generation jobs and results
  APIs; Phase 2 can read `environment` and `schema_version` from an optional
  rehearsal report API.
- Empty/error states: show "No generation jobs yet" when jobs are empty; show
  normal query error alert if jobs or results fail to load.
- Test expectation: render summary counts from mocked `listGenerationJobs` and
  `listGenerationResults`; show `mock`/`not real Agnes` copy only when data
  proves mock or report API provides it.

### 2. Shot Scenario Matrix

- What it shows: one row per shot with expected scenario, actual scenario, pass
  state, latest status, and selected result state.
- Why it matters: operators can quickly see `SHOT_001 source success` and
  `SHOT_002 source failed + rerun success`.
- Data source: Phase 1 infers actual scenario from existing jobs/results:
  completed first attempt means `source_success`; failed first attempt followed
  by completed later attempt means `source_failed_then_rerun_success`. Phase 2
  can use report `scenarios` when available.
- Empty/error states: no rows when no jobs exist; blocked inference shows
  `unknown` rather than inventing a pass/fail.
- Test expectation: mocked data with one completed first attempt and one failed
  then completed rerun renders both expected labels and pass badges.

### 3. Shot Timeline / Attempt History

- What it shows: attempt number, job ID, status, error code, provider job ID,
  created/updated/completed timestamps.
- Why it matters: preserves evidence that failed attempts were retained and
  reruns created new attempts.
- Data source: existing `GET /api/chapters/{chapter_id}/generation/jobs`.
- Empty/error states: empty timeline message for shots without jobs; error
  alert on job query failure.
- Test expectation: failed first attempt remains visible after a completed
  second attempt; error code `generation_failed` is displayed.

### 4. Result Version History

- What it shows: result ID, source job ID, attempt number, media type, source
  URL state, local result availability, local content URL.
- Why it matters: lets operators confirm version history and local result
  persistence.
- Data source: existing `GET /api/chapters/{chapter_id}/results`.
- Empty/error states: show "No video results yet"; show warning when
  `source_url_expired` and `local_result_available` is false.
- Test expectation: expired source URL with local content shows playable local
  link; expired source URL without local content shows missing artifact warning.

### 5. Current Selection Indicator

- What it shows: current adopted result per shot, result ID, attempt number, and
  whether selected result came from source or rerun.
- Why it matters: confirms the chapter has an adopted result, not only candidate
  versions.
- Data source: existing `current_result_id` from results API plus matching
  result/job attempt numbers.
- Empty/error states: show `No result selected` when results exist but
  `current_result_id` is empty.
- Test expectation: selected rerun result for SHOT_002 renders as current and
  source failed result remains non-current.

### 6. Review Status Panel

- What it shows: latest review decision, review ID, failure category, and note
  per selected result.
- Why it matters: review completion is part of M4 rehearsal acceptance.
- Data source: needs API extension; current UI can create reviews but cannot
  list them. Until then, report-only `reviews` can appear only through a report
  API.
- Empty/error states: show `Not reviewed` if no review is returned; keep review
  action buttons available.
- Test expectation: after API extension, mocked review data renders `passed`
  with review ID for each selected result.

### 7. Local Artifact Preview / Link

- What it shows: video preview using `local_content_url` when available, source
  URL state, and a copyable local content link.
- Why it matters: proves local video bytes were persisted and are viewable
  without provider URL availability.
- Data source: existing results API and `/api/results/{result_id}/content`.
  `object_id` remains runtime-report-only unless Phase 2 exposes it.
- Empty/error states: when local result is missing and source URL expired, show
  "Local artifact missing; rerun required".
- Test expectation: preview uses local content URL before source URL and does
  not autoplay.

### 8. Deferred Real Provider Banner

- What it shows: `Real Agnes smoke test deferred`, provider mode, and
  `AUTHORIZE_REAL_AGNES_VIDEO_SMOKE_TEST`.
- Why it matters: prevents mock rehearsal from being mistaken for real provider
  validation.
- Data source: Phase 1 static banner gated to rehearsal mode or report view;
  Phase 2 uses report `environment` and `deferred_items`.
- Empty/error states: if environment is unknown, show neutral "Provider smoke
  status unavailable" rather than claiming real readiness.
- Test expectation: banner displays deferred token in rehearsal/report view and
  does not imply real Agnes network validation.

## Data Mapping

| M4 report field | UI use | Current availability |
| --- | --- | --- |
| `schema_version` | Summary metadata, report compatibility warning | runtime report only |
| `environment.provider` | Summary card provider label | runtime report only; Phase 1 can infer mock only in verifier/report context |
| `environment.real_agnes_request_made` | Deferred provider banner and summary | runtime report only |
| `scenarios` | Shot Scenario Matrix expected/actual/pass | runtime report only; Phase 1 can derive actual scenario from existing jobs/results |
| `job_status_timeline` | Shot Timeline / Attempt History | existing API via `/generation/jobs` |
| `result_versions` | Result Version History | existing API via `/results` |
| `current_selection` | Current Selection Indicator | existing API via `current_result_id` |
| `reviews` | Review Status Panel | needs API extension; currently runtime report only after verifier |
| `failure_categories_tested` | Failure Coverage and scenario badge notes | runtime report only; job `error_code` exists through existing API |
| `local_content_urls` | Local Artifact Preview / Link | existing API via result `local_content_url` |
| `object_ids` | Deep artifact audit/debug label | runtime report only; do not expose in Phase 1 unless needed |
| `operator_checklist` | Operator Checklist panel | runtime report only; Phase 3 can add persisted checklist state |
| `deferred_items` | Deferred Real Provider Banner | runtime report only; Phase 1 may use static documented token |

## Operator Workflow

1. Open a chapter with generated M4 rehearsal data.
2. Go to the existing generation/results workspace.
3. Read the Chapter Rehearsal Summary Card.
4. Scan the Shot Scenario Matrix for failed rows or unknown scenarios.
5. Open a shot timeline to confirm source attempts and rerun attempts.
6. Inspect Result Version History and Current Selection.
7. Preview local artifact or open the local content link.
8. Check Review Status.
9. Read the Deferred Real Provider Banner before communicating results.

## Non-Scope

- No real Agnes request.
- No public HTTPS setup.
- No provider main-chain changes.
- No M3/M4 verifier behavior change.
- No video quality scoring.
- No checklist persistence in Phase 1.
- No new dashboard outside the existing generation/results workspace.
- No LibTV, subtitles, BGM, timeline, final export, or collaboration features.

## Implementation Phases

### Phase 1: Read-only UI Using Existing Generation/Results APIs

Scope:

- Add a small read-only summary area to the existing generation/results
  workspace.
- Derive timeline, rerun, selection, and artifact state from existing jobs and
  results APIs.
- Show a static deferred-provider warning in rehearsal context.
- Keep review actions as they are; label review status as unavailable unless
  the API returns review data later.

Files likely touched:

- `web/src/features/generation/AgnesGenerationTab.tsx`
- `web/src/features/generation/GenerationResultsTab.tsx`
- `web/src/features/generation/api.ts`
- Existing generation component tests.

### Phase 2: Add Optional Rehearsal Report API If Needed

Scope:

- Add a read-only endpoint for the latest M4 rehearsal report if product needs
  exact report fields in the browser.
- Expose only non-secret, runtime-report fields.
- Keep runtime report optional; UI must still work from jobs/results APIs.

Files likely touched:

- `ai_drama_web/routers/generation.py` or a small report router.
- `web/src/features/generation/api.ts`
- Web tests and focused router tests.

### Phase 3: Add Operator Checklist State If Needed

Scope:

- Persist checklist completion only if operators need in-app handoff state.
- Keep checklist scoped to rehearsal/report review, not general production
  workflow.

Files likely touched:

- Product store schema/migration only if persistence is required.
- One small API surface for checklist state.
- One focused UI panel and tests.

## Acceptance Criteria

- Operator can identify chapter-level rehearsal state without opening JSON.
- SHOT_001 source success is visible.
- SHOT_002 source failure and rerun success are visible.
- Attempt number, job ID, status, and error code are visible per attempt.
- Result ID, source job, local content URL, and current selection are visible.
- Local artifact preview/link is available when `local_result_available` is
  true.
- Missing local artifact plus expired source URL is clearly warned.
- Review status is either shown from API/report data or explicitly marked
  unavailable in Phase 1.
- Deferred real provider status and
  `AUTHORIZE_REAL_AGNES_VIDEO_SMOKE_TEST` are visible.
- UI copy does not imply that real Agnes behavior or video quality was tested.

## Test Plan

Phase 1 tests:

- Extend `AgnesGenerationTab.test.tsx` or `GenerationResultsTab.test.tsx` with
  a mock chapter containing SHOT_001 completed attempt and SHOT_002 failed then
  completed rerun.
- Assert summary counts, scenario labels, attempt history, failed error code,
  current selection, local artifact link, and deferred-provider banner.
- Assert no autoplay on video preview.
- Assert empty jobs/results render neutral empty states.

Phase 2 tests:

- Add router/API tests for optional report endpoint if implemented.
- Add UI test that report fields override inferred scenario fields.
- Assert report endpoint does not expose secrets or real provider credentials.

Phase 3 tests:

- Add one focused test for checklist persistence only if checklist state is
  implemented.

Regression commands:

```bash
python3 tools/verify_m4_chapter_rehearsal.py
python3 -m pytest -q
npm --prefix web run test -- --run
npm --prefix web run build
npm --prefix web run test:e2e
git diff --check
```

## Risks

- Overbuilding a dashboard when the existing generation/results workspace is
  enough.
- Confusing mock rehearsal with real Agnes validation.
- Deriving scenario pass/fail incorrectly when jobs are incomplete.
- Review status may remain write-only until an API extension exists.
- Exposing `object_id` may be useful for debugging but noisy for operators.
- Runtime report API could couple UI to verifier artifacts; keep it optional.

## Recommended Phase 1 Scope

Start with read-only UI using existing jobs/results APIs:

- Chapter Rehearsal Summary Card
- Shot Scenario Matrix with derived scenarios
- Shot Timeline / Attempt History
- Result Version History
- Current Selection Indicator
- Local Artifact Preview / Link
- Deferred Real Provider Banner

Skip persisted checklist state, report API, and review history display until
operator use proves they are needed.
