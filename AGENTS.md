## Phase 1 — Storyboard Canonicalization

Before any Phase 1 planning, implementation, testing, review, commit,
or push, read these files in full:

- `docs/superpowers/specs/2026-06-28-storyboard-canonical-shot-prompt-foundation-design.md`
- `docs/superpowers/specs/2026-06-29-phase-1-agent-execution-acceptance-contract.md`

Rules:

- Treat both documents as frozen and read-only.
- The Foundation Design defines the architecture.
- The Phase 1 contract defines execution, stop conditions, scope,
  verification, and completion.
- Do not modify either frozen document.
- Do not implement Phase 2 or later scope while performing Phase 1 work.
- The main agent is the only code-writing agent.
- Subagents are read-only unless the contract explicitly says otherwise.
- Stop and ask the user only when a contract Stop Condition is triggered.
- Do not weaken tests, schemas, fixtures, golden outputs, or acceptance checks.
- Do not declare completion without the unified Phase 1 verification PASS.
- Do not commit or push partial work after a Stop Condition.

---

## AI Drama Web Production MVP — Milestone 3

Milestone 1 and Milestone 2 are complete and together form the required
implementation baseline.

The active product milestone is:

```text
Milestone 3 — Agnes Video Generation, Persistent Jobs, Results, and Rerun
```

### Authority Order

Before any Milestone 3 design, planning, implementation, testing, review,
commit, or push, read the following documents in full:

1. Product scope authority:

   `docs/superpowers/specs/2026-07-05-ai-drama-web-production-mvp-design-v2.md`

2. Program and milestone sequencing authority:

   `docs/superpowers/plans/2026-07-05-ai-drama-web-production-mvp-implementation-program.md`

3. Current implementation authority:

   `docs/superpowers/plans/2026-07-05-m3-agnes-generation-results-rerun.md`

4. Existing visual-system baseline:

   `docs/product-design/m1/`
   `docs/product-design/m2/`

5. Milestone 3 Product Design authority, after it is approved:

   `docs/product-design/m3/`

6. Current runtime, provider, Web, and test implementation:

   `ai_drama_runtime/`
   `ai_drama_web/`
   `web/`
   `tests/`

7. Current official Agnes Video documentation.

8. Secondary Agnes support material only:

   `https://github.com/lj1270998580-crypto/Agnes-help-skill`

When documents conflict, apply this priority:

```text
MVP Design Spec
→ M3 Implementation Plan
→ approved M3 Product Design handoff
→ existing runtime and M1/M2 contracts and tests
→ current official Agnes Video documentation
→ Agnes Help Skill as secondary guidance
```

Product Design documents control page layout, interaction, component behavior,
screen states, and visual continuity. They do not override runtime,
persistence, job-state, idempotency, provider-contract, or security
architecture.

### Branches

Use these branch roles:

```text
docs/m3-product-design
→ M3 Product Design documents and prototype evidence only

feat/mvp-agnes-generation
→ M3 production implementation only
```

Do not implement production code on `docs/m3-product-design`.

Do not perform open-ended Product Design exploration on
`feat/mvp-agnes-generation`.

Do not continue M3 work on the merged Milestone 2 branch.

### Product Design Gate

Before any Milestone 3 production implementation, all of the following must
exist and be approved:

- `docs/product-design/m3/brief.md`
- `docs/product-design/m3/information-architecture.md`
- `docs/product-design/m3/workflow-map.md`
- `docs/product-design/m3/interaction-spec.md`
- `docs/product-design/m3/screen-states.md`
- `docs/product-design/m3/component-inventory.md`
- `docs/product-design/m3/visual-tokens.md`
- `docs/product-design/m3/selected-direction.md`
- `docs/product-design/m3/implementation-handoff.md`

`selected-direction.md` must identify exactly one approved direction.

`implementation-handoff.md` must define:

- chapter-workspace routes and tab structure;
- Generation and Results/Rerun page composition;
- primary components;
- API data dependencies;
- waiting, queued, submitting, submitted, polling, completed, failed,
  cancelled, result-expired, and submission-outcome-unknown states;
- empty, loading, blocked, retryable, terminal, and recovered states;
- batch-submit and duplicate-click behavior;
- polling indicators and manual refresh;
- video preview behavior;
- result version history and current selection;
- rerun drawer fields and allowed overrides;
- responsive behavior;
- reusable Milestone 1 and Milestone 2 components;
- design decisions the implementation agent must not change.

If these files are missing, incomplete, or unapproved:

- do not write Milestone 3 business code;
- do not infer a final UI from the implementation plan;
- output `M3_PREFLIGHT_BLOCKED_BY_DESIGN`;
- stop and request completion or approval of the M3 Product Design package.

### Authorization Gate

Before the user sends:

```text
AUTHORIZE_M3_IMPLEMENTATION
```

the agent may only:

- inspect the repository;
- read specifications, plans, code, tests, and design files;
- install existing declared dependencies to establish a baseline;
- run tests, builds, verifiers, and read-only analysis;
- verify the current official Agnes Video request and polling contract;
- prepare and report a Milestone 3 Preflight;
- work on the dedicated Product Design documentation branch when explicitly
  instructed to perform the M3 Product Design Sprint.

Before authorization, do not:

- create or alter production database tables;
- modify runtime, API, Poller, Provider, or production frontend code;
- submit Agnes video requests;
- create implementation commits.

A valid implementation preflight must end with exactly one of:

```text
M3_PREFLIGHT_READY
M3_PREFLIGHT_BLOCKED
M3_PREFLIGHT_BLOCKED_BY_DESIGN
```

Only `M3_PREFLIGHT_READY` followed by the explicit authorization token permits
production implementation.

### Milestone 3 In Scope

Implement only the Milestone 3 plan.

#### Generation Job and Result Persistence

Implement additive persistence for:

- generation jobs;
- provider job identifiers;
- job attempts;
- request hashes;
- idempotency keys;
- provider request and response object references;
- result records;
- result metadata;
- one current selected result per chapter shot;
- result reviews;
- immutable rerun records.

The required internal job states are:

```text
draft
queued
submitting
submitted
polling
completed
failed
cancelled
```

Allowed transitions must be enforced centrally:

```text
draft -> queued
queued -> submitting | cancelled
submitting -> submitted | failed
submitted -> polling | completed | failed
polling -> polling | completed | failed
completed | failed | cancelled -> terminal
```

Do not allow arbitrary state mutation from routers or React components.

#### Controlled Asset Delivery

Implement signed temporary image delivery for provider-reachable inputs.

Required baseline route:

```text
GET /public/assets/{asset_id}?expires=...&signature=...
```

Rules:

- use HMAC SHA-256;
- verify signatures with `hmac.compare_digest()`;
- reject altered asset IDs, altered expiry, and invalid signatures;
- reject expired URLs;
- reject non-image assets;
- use `AI_DRAMA_PUBLIC_BASE_URL`;
- reject localhost, loopback, local file paths, and otherwise
  provider-unreachable URLs for real Agnes submissions;
- never include the Agnes API key in a signed asset URL.

#### Agnes Video Provider Integration

Implement Agnes Video behind the existing provider abstraction.

At implementation time, verify the current official contract for:

- submission endpoint;
- polling endpoint;
- result endpoint or response field;
- model identifier;
- text-to-video input;
- image-to-video input;
- multi-image or keyframe input;
- prompt field;
- negative-prompt support;
- duration support;
- aspect-ratio or resolution support;
- `video_id`;
- `task_id`;
- provider status values;
- error response format;
- rate limits;
- result URL lifetime.

Current expected baseline:

```text
model: agnes-video-v2.0
provider job identifier: video_id
task_id: raw provider metadata only
```

Do not silently substitute `task_id` for `video_id`.

If the current official Agnes documentation conflicts with the expected
baseline, stop and report the exact conflict before changing the contract.

#### Idempotent GenerationJobService

The GenerationJobService must:

- accept only current ready Shot Prompt revisions;
- require usable and provider-reachable assets;
- build a canonical provider request;
- persist the request in immutable object storage;
- compute a deterministic request hash;
- enforce provider plus idempotency-key uniqueness;
- persist `queued` before returning;
- return the existing job for duplicate normal submissions;
- create a new attempt only through an explicit rerun;
- keep prior jobs and prior results unchanged.

Canonical request hashes must use deterministic JSON serialization:

```python
json.dumps(
    payload,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
    allow_nan=False,
)
```

#### Persistent Single-Process Poller

Implement a SQLite-backed, single-process Poller started through FastAPI
lifespan.

Required configuration:

```text
AI_DRAMA_AGNES_VIDEO_RPM
AI_DRAMA_AGNES_POLL_INTERVAL_SECONDS
```

Required behaviors:

- persist `submitting` before the submission network call;
- persist the provider job ID immediately after successful submission;
- poll only nonterminal due jobs;
- respect the configured submission rate limit;
- recover queued, submitted, and polling jobs after application restart;
- avoid duplicate submission after restart;
- when a job is `submitting` without a known provider job ID, mark it with
  `submission_outcome_unknown` rather than blindly resubmitting;
- persist the next poll time;
- make one-cycle execution directly testable.

Do not add Redis, Celery, distributed locks, or external queue infrastructure.

#### Result Persistence and Selection

The result service must:

- fetch exact provider result bytes;
- persist result bytes in immutable object storage;
- persist metadata separately;
- retain all prior result versions;
- maintain one selected result per chapter shot through a selection record;
- never delete prior results when selection changes;
- record result reviews and failure categories;
- handle expired provider URLs explicitly.

Normalize provider and workflow failures to:

```text
authentication
rate_limited
invalid_request
input_unreachable
provider_busy
generation_failed
timeout
result_expired
unknown_provider_error
submission_outcome_unknown
```

#### Immutable Rerun Workflow

An explicit rerun may override only approved fields, including:

- positive prompt;
- negative prompt;
- selected assets;
- generation mode;
- duration;
- provider-supported video parameters approved by the M3 design and API
  contract.

A rerun must:

- preserve the source job;
- preserve prior results;
- create a new generation job;
- increment attempt number;
- persist the exact overrides in immutable object storage;
- persist a rerun record linking source and new job.

#### Generation, Results, and Rerun APIs

Implement the M3 API surface defined by the implementation plan, including:

```text
POST /api/chapters/{chapter_id}/generation/video-jobs
GET  /api/chapters/{chapter_id}/generation/jobs
GET  /api/generation/jobs/{job_id}
POST /api/generation/jobs/{job_id}/refresh
GET  /api/chapters/{chapter_id}/results
POST /api/shots/{shot_id}/results/{result_id}/select
POST /api/results/{result_id}/review
POST /api/generation/jobs/{job_id}/rerun
```

Routers must only map HTTP inputs and outputs.

Job transitions, idempotency, provider calls, result persistence, selection,
and rerun logic belong in services and stores.

#### Generation and Results Web UI

Implement the approved M3 Product Design for:

- Agnes Generation tab;
- Results and Rerun tab;
- ready and blocked shots;
- batch submit;
- single-shot submit;
- prompt, asset, and parameter preview;
- waiting, generating, success, failed, and recovered states;
- React Query polling only while nonterminal jobs exist;
- manual refresh;
- duplicate-click protection;
- non-autoplay video preview;
- version history;
- current-result selection;
- source job, prompt, asset, and attempt details;
- failure review categories;
- rerun drawer;
- retention of prior result versions.

Milestone 3 unlocks:

```text
Agnes 生成
结果与重跑
```

### Milestone 3 Out of Scope

Do not implement:

- LibTVBackend or LibTV execution;
- dubbing;
- subtitles;
- BGM;
- sound effects;
- timeline editing;
- video trimming;
- video concatenation;
- transitions;
- color grading;
- final episode export;
- publishing;
- multi-user authentication or permissions;
- collaboration;
- generic workflow engines;
- generic Agent runtimes;
- provider plugin marketplaces;
- PostgreSQL;
- Redis;
- Celery;
- distributed queues;
- distributed workers;
- microservices;
- Kubernetes;
- Milestone 4 real-chapter acceptance work;
- historical Phase 3B–3E governance, qualification, or verifier expansion.

Navigation or documentation for later work may exist, but no later-milestone
implementation may be added.

### Existing Behavior That Must Be Preserved

Preserve all Milestone 1, Milestone 2, and historical runtime behavior:

- `RuntimeStore`;
- immutable object storage;
- Artifact and Revision semantics;
- Approval and Validator behavior;
- Script Workflow;
- Storyboard Workflow;
- Canonical Storyboard validation and rendering;
- Bundle behavior;
- Phase 3A Shot Prompt artifact and business-key foundation;
- project, chapter, and source persistence;
- persistent chapter discovery;
- Production Profiles;
- Asset Studio;
- Agnes Image generation;
- Asset Requirement Analysis;
- Shot Prompt canonical format;
- Shot Prompt Skill;
- ShotPromptService;
- M1 and M2 Web APIs;
- M1 and M2 chapter-workspace UI;
- all M1 and M2 verifiers and tests.

Do not duplicate existing runtime logic inside FastAPI routers or React
components.

Do not change Shot Prompt readiness semantics merely to allow video submission.

### Persistence Rules

- New tables and columns must be additive.
- Do not destructively rewrite historical tables.
- Use the existing SQLite database and immutable object store.
- Provider request bodies, provider responses, result bytes, result metadata,
  and rerun overrides must be stored according to the M3 implementation plan.
- Store object identifiers and hashes in relational rows.
- Preserve referential integrity and project/chapter/shot scoping.
- Migrations must remain compatible with existing migration preview and
  current-version checks.
- A rerun of migrations must be idempotent.
- Result selection must not delete or overwrite prior result records.

### Secret and Security Rules

- Read the Agnes API key only through the existing `LocalSecretStore`.
- Never accept an Agnes API key in generation request bodies.
- Never return the full key to the browser.
- Never write the key to logs, artifacts, provider metadata, test snapshots,
  exceptions, exported bundles, or Git history.
- Sanitize Authorization headers, API-key fields, tokens, and secret-like
  strings from provider request and response evidence.
- Signed public asset URLs must not contain secrets beyond the URL signature.
- Use constant-time comparison for signatures.
- Real provider tests must be explicit opt-in and must not run in the default
  test suite.

### Testing and Development Rules

Use test-driven development.

For every implementation task:

1. write the focused failing test;
2. run it and confirm the expected failure;
3. implement the minimum code required;
4. run focused tests;
5. run affected regression tests;
6. perform specification-compliance review;
7. perform code-quality review;
8. fix findings;
9. rerun focused and affected tests;
10. create one focused commit;
11. continue to the next task.

Do not weaken, skip, delete, or rewrite existing tests merely to make a change
pass.

Keep implementation aligned with the exact task order in:

`docs/superpowers/plans/2026-07-05-m3-agnes-generation-results-rerun.md`

### Agent Collaboration Rules

- Use subagent-driven development after authorization.
- The main agent coordinates, reviews, integrates, and owns final decisions.
- At most one code-writing implementer may operate at a time.
- Read-only exploration, test analysis, official-document verification, and
  review agents may run in parallel.
- Subagents must receive the current task scope and forbidden-scope list.
- Do not allow multiple write agents to modify overlapping files.
- Do not begin the next task until the current task has passed focused tests,
  review, and commit.

### Commit and Push Rules

- Keep one focused commit per implementation task.
- Do not combine all Milestone 3 work into a single commit.
- Do not amend or rewrite historical Milestone 1 or Milestone 2 commits.
- Do not push unless the user explicitly authorizes publication.
- Do not merge to `main`.
- Do not begin Milestone 4 after Milestone 3 completion.

### Stop Conditions

Stop and report instead of improvising when:

- required M3 Product Design files are missing or not approved;
- the selected M3 design direction is ambiguous;
- the current branch does not contain the complete merged M1 and M2 baseline;
- current official Agnes Video documentation conflicts with the planned
  provider contract;
- the provider does not return a stable queryable job identifier;
- the provider requires an input mode unsupported by the approved M3 design;
- a real submission would require localhost, a local file path, or another
  provider-unreachable asset URL;
- a required migration would destructively alter historical data;
- baseline tests fail for reasons unrelated to the current task;
- the implementation plan conflicts materially with the approved MVP Design;
- a proposed change requires LibTV, post-production, distributed
  infrastructure, or Milestone 4 scope;
- a secret would need to be exposed to the browser, logs, artifacts, or
  repository;
- restart recovery cannot avoid duplicate or unknown-outcome submissions
  without changing the approved architecture.

Do not commit or push partial work after a Stop Condition.

### Milestone 3 Verification

Before declaring completion, run all verification commands required by the M3
implementation plan, including at minimum:

```bash
python3 tools/verify_m1_web_workflow.py
python3 tools/verify_m2_assets_shot_prompts.py
python3 tools/verify_m3_agnes_generation.py
python3 migration/tools/verify_migration.py
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q
npm --prefix web run test -- --run
npm --prefix web run build
npm --prefix web run test:e2e
```

Default verification must use the fake provider or mocked Agnes HTTP
contracts. Real Agnes network tests are opt-in only.

Browser or Playwright verification must cover:

- ready-shot selection;
- blocked-shot explanation;
- single-shot submission;
- batch submission;
- duplicate-click protection;
- waiting, generating, completed, and failed states;
- manual refresh;
- nonterminal polling;
- result preview without autoplay;
- result version history;
- result selection;
- failure category review;
- rerun creation;
- prior result retention;
- restart recovery;
- no LibTV or post-production implementation.

### Completion Status

Only declare Milestone 3 complete when:

- all M3 implementation-plan tasks are complete;
- all focused and regression tests pass;
- migration verification passes;
- the M1 verifier still passes;
- the M2 verifier still passes;
- the M3 verifier passes;
- frontend tests and build pass;
- M3 E2E and Browser QA pass;
- fake-provider restart recovery passes;
- idempotency and duplicate-submission tests pass;
- no secret is exposed;
- the working tree is clean;
- no Milestone 4, LibTV, or post-production scope was implemented.

The final status must be exactly one of:

```text
M3_COMPLETE
M3_BLOCKED
M3_FAILED
```

After `M3_COMPLETE`, stop. Do not start Milestone 4.
