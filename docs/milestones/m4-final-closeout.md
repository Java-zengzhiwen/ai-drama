# M4 Final Closeout

## Purpose

Close out M4 as a completed mock-provider chapter rehearsal milestone and make
the boundary to M5 explicit.

M4 is complete for chapter-level rehearsal, reporting, runbook, planning, and
read-only UI visibility. Real Agnes smoke testing remains deferred.

## Final M4 Scope

M4 focused on proving the chapter-level generation workflow under the mock
provider:

- source material and chapter setup;
- current ready shot prompt revision;
- usable image assets;
- video job queueing;
- poller execution;
- failed attempt retention;
- rerun creation;
- local video result persistence;
- current result selection;
- review write path;
- operator report;
- read-only UI visibility.

## Completed Deliverables

- M4 chapter rehearsal verifier:
  `1935dc3f32626fa5df57abf8fd7f694bc6f30e64`
- M4 rehearsal JSON/Markdown report:
  `1935dc3f32626fa5df57abf8fd7f694bc6f30e64`
- M4 rehearsal runbook:
  `f60d669e52d97b6558b6cd014a27870f9beaeaa7`
- M4 UI visibility plan:
  `f848a7b148fb27e72ea88176ef6261ce15acfdbe`
- M4 Phase 1 read-only UI visibility panel:
  `bcb4353af9fbd3800f673dad7ba1e481815119a8`

## Verification Commands

M4 closeout relies on the verification already run during the milestone merges:

```bash
python3 tools/verify_m4_chapter_rehearsal.py
python3 -m pytest -q
python3 tools/verify_m1_web_workflow.py
python3 tools/verify_m2_assets_prompts.py
python3 tools/verify_m2_assets_shot_prompts.py
python3 tools/verify_m3_agnes_generation.py
python3 migration/tools/verify_migration.py
npm --prefix web run test -- --run
npm --prefix web run build
npm --prefix web run test:e2e
git diff --check
```

Expected M4 rehearsal token:

```text
M4_CHAPTER_REHEARSAL_PASS
```

## Production Meaning

M4 proves that the chapter-level generation workflow is traceable under mock
provider:

- ready shot prompt revision;
- queued video jobs;
- poller execution;
- failed attempt retention;
- rerun creation;
- local result persistence;
- current result selection;
- review write path;
- operator report;
- read-only UI visibility.

This means operators can rehearse and inspect the generation chain without
spending provider credits or depending on public HTTPS asset hosting.

## Non-Scope

M4 does not validate:

- real Agnes network behavior;
- public HTTPS asset delivery;
- Agnes API key configuration;
- real video quality;
- full production chapter export;
- subtitles / BGM / final timeline;
- LibTV execution.

## Deferred Items

Real Agnes smoke test remains deferred behind:

```text
AUTHORIZE_REAL_AGNES_VIDEO_SMOKE_TEST
```

Deferred work:

- configure real provider runtime;
- verify public signed asset URL reachability from Agnes;
- submit one authorized real Agnes video smoke request;
- record real provider job status/result behavior;
- keep real-provider evidence separate from mock rehearsal evidence.

## Transition to M5

M5 should focus on Real Provider Readiness and Agnes Smoke Test.

M5 requires:

- public HTTPS `AI_DRAMA_PUBLIC_BASE_URL`;
- Agnes API key in `LocalSecretStore`;
- `AI_DRAMA_RUNTIME_PROVIDER=agnes`;
- successful signed asset URL reachability;
- explicit authorization token before any real video generation request:
  `AUTHORIZE_REAL_AGNES_VIDEO_SMOKE_TEST`.
