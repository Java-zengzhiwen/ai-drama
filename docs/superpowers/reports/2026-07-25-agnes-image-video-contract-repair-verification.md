# Agnes Image And Video Contract Repair Verification

Date: 2026-07-26

## Result

The approved Agnes image and video contract repair is implemented on
`feat/agnes-image-video-contract-repair`. The implementation preserves the two
existing stable models, keeps production supplier execution disabled by
default, and makes no real Provider request during implementation or
verification.

```text
IMPLEMENTATION_STARTED=true
PRODUCTION_FLAG_ENABLED=false
REAL_PROVIDER_REQUESTS=false
REAL_TEXT_REQUEST_COUNT=0
REAL_IMAGE_REQUEST_COUNT=0
REAL_VIDEO_REQUEST_COUNT=0
```

## Scope Delivered

- `agnes-image-2.1-flash` accepts manifest-driven size tiers, exact legacy
  dimensions, and aspect ratios. Reference images remain ordered in
  `extra_body.image`.
- Image model-row tests expose only constraints declared by the immutable model
  revision. Video models continue to omit a model-row real test and direct the
  user to the project Shot generation workflow.
- `agnes-video-v2.0` accepts normal mode with zero or one image and keyframes
  mode with two or three ordered images.
- Video submit accepts only the approved mode values, validates frame rate and
  the `8n+1` frame-count rule before network, and requires an explicit
  `video_id` or `data.video_id` in the response.
- Poll and fetch use only `video_id`. Completed output resolves
  `metadata.url` first and the Worker accepts only `video/mp4` bytes with an
  MP4 `ftyp` signature.
- Durable image jobs, per-job snapshot routing, restart-safe video polling,
  result persistence, evidence sanitization, and legacy compatibility remain
  covered by the M6C regression suite.

No Agnes text model, second Agnes supplier, new Agnes model, video model-row
real test, automatic retry, fallback, or batch operation was introduced.

## TDD Evidence

The review corrections were implemented from failing tests:

- Generic `id` and `task_id` responses were initially accepted as video IDs.
- Invalid `mode`, `num_frames`, and `frame_rate` initially reached the fake
  network helper.
- Invalid MP4 bytes and incorrect media types were initially accepted.
- The video model inspector initially lacked the project Shot verification
  guidance.
- The new manifest initially omitted legacy exact sizes `1024x1536` and
  `1536x1024`.

After implementation, the focused correction suites passed:

```text
Agnes adapter tests: 17 passed
Generation job and execution focused tests: 57 passed
Worker tests: 37 passed
Supplier models panel tests: 12 passed
AGNES-IV semantic verifier: 12/12 PASS
```

## Final Verification

All commands below ran after the last HIGH finding was fixed in commit
`51611b54872707846143d0fa944967839131e215`.

| Command | Result |
| --- | --- |
| `PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q` | `796 passed, 1 skipped` |
| `npm --prefix web run test -- --run` | `165 passed, 5 skipped` |
| `npm --prefix web run build` | PASS |
| `npm --prefix web run test:e2e` | `12 passed` |
| `npm --prefix worker test` | `37 passed` |
| `python3 tools/verify_m3_agnes_generation.py` | `M3_AGNES_GENERATION_PASS` |
| `python3 tools/verify_m4_chapter_rehearsal.py` | `M4_CHAPTER_REHEARSAL_PASS` |
| `python3 tools/verify_m6c_adapter_cutover.py` | `M6C-001..015 PASS` |
| `python3 tools/verify_agnes_image_video_contract.py` | `AGNES-IV-001..012 PASS` |
| `python3 migration/tools/verify_migration.py` | `valid`, 81 files checked |
| `git diff --check` | PASS |

The M4 verifier produced only ignored files under `runtime-data/`; they are not
tracked or included in this handoff.

## Acceptance Mapping

| Key | Evidence |
| --- | --- |
| AGNES-IV-001 | Stable Agnes Image and Video identities and immutable manifest options |
| AGNES-IV-002 | Text-to-image request contract |
| AGNES-IV-003 | Image-to-image `extra_body.image` contract |
| AGNES-IV-004 | Durable image job, result, asset linkage, and ratio propagation |
| AGNES-IV-005 | Video submit exactly once across restart boundaries |
| AGNES-IV-006 | Explicit `video_id`, mode/frame validation, and `video_id`-only polling |
| AGNES-IV-007 | `metadata.url` precedence and MP4 media validation |
| AGNES-IV-008 | Restart-safe completion and local result persistence |
| AGNES-IV-009 | Snapshot and active legacy Agnes compatibility |
| AGNES-IV-010 | Image model-row test only; video Shot workflow guidance |
| AGNES-IV-011 | Credential and signed-URL evidence sanitization |
| AGNES-IV-012 | Production flag off plus Python, Node Worker, and Web network-denial guards |

## Security Evidence

- Python Worker isolation, Node Worker transport denial, and Web default
  network denial all passed.
- `ai_drama_web/config.py` keeps `m6_supplier_execution_enabled` false by
  default.
- No database or `runtime-data` path is tracked.
- The tracked secret scan found only previously documented synthetic fixture
  values such as `Bearer echoed-provider-token`; no real API key, credential,
  signed URL, private media, or Provider response is included.
- The semantic verifier reports text, image, and video real request counters as
  zero and requires all three network-denial layers to pass.

## Review History

- The first specification review found four HIGH issues: generic ID fallback,
  missing video parameter validation, missing MP4 validation, and insufficient
  zero-network evidence. Commit `6e0783d` fixed all four.
- The first technical/security review additionally found the two omitted legacy
  exact image sizes. Commit `6e0783d` restored both.
- Both follow-up reviewers independently found unsupported video modes being
  silently treated as normal mode. Commit `51611b5` added fail-closed
  `INVALID_VIDEO_MODE` validation and a zero-network regression test.
- Specification/acceptance reviewer confirmed exact commit `51611b5`: PASS;
  blockers NONE; high findings NONE.
- Architecture/technical/security review of `6e0783d` found only the unsupported
  mode HIGH and confirmed the prior media, size, ID, network, credential, and
  snapshot findings closed. Commit `51611b5` closes that final HIGH; the
  post-fix focused tests, full baseline, three network-denial layers, and all
  semantic verifiers passed. A second acknowledgement attempt was interrupted
  by reviewer quota, so this report records the exact evidence without
  inventing an additional reviewer verdict.

## Rollback

Production supplier execution remains disabled by default. Operational rollback
is to keep `AI_DRAMA_M6_SUPPLIER_EXECUTION_ENABLED=false` and restore the prior
immutable Agnes supplier version as current. Source rollback is a normal revert
of the feature commits; no history rewrite or destructive migration is needed.
