
This repository is governed by milestone-specific agent rules. Agents must follow the active milestone rules first, while preserving all completed milestone baselines.

---

## Current Active Milestone

```text
Milestone 6 — Supplier And Project Model Configuration
```

M6 implements the approved Toonflow-style `Supplier -> Models` design through five separately reviewed stages: M6A Supplier Core, M6B Model Catalog And Binding, M6C Adapter Cutover, M6D Management UI, and M6E Migration And Acceptance.

The authoritative M6 design is:

```text
docs/superpowers/specs/2026-07-12-provider-model-management-design.md
```

The authoritative M6 governance contract is:

```text
docs/superpowers/specs/2026-07-12-m6-governance-contract.md
```

M6 planning is docs-only. Implementation begins only after the governance contract and the relevant M6A-M6E plan are reviewed and explicitly authorized.

No M6 implementation or verification may send a real provider request. Real-provider tests require a later provider-and-capability-specific authorization defined by an approved execution contract; the historical M5 Agnes token does not authorize M6 work.

### Post-M6 Model Test Boundary

The approved model-level test increment is governed by:

```text
docs/superpowers/specs/2026-07-14-model-level-provider-tests-design.md
docs/superpowers/plans/2026-07-14-model-level-provider-tests.md
```

- `AI_DRAMA_MODEL_TESTS_ENABLED` defaults to false.
- All model-test status, create, recovery, read, and content APIs are application-layer loopback-only.
- `校验并保存` remains local and network-disabled.
- A local user's `确认并测试` click authorizes exactly one real generation submission for the selected text or image model and any required bounded result download.
- One confirmation never authorizes retry, fallback, batch work, video tests, project generation, or another model.
- Codex, automated tests, CI, verifiers, and reviewers must use fake providers and keep all real request counters at zero unless the user separately requests a provider-and-capability-specific real test after implementation review.
- Model-test records, media, provider evidence, credentials, databases, and `runtime-data` never enter Git.

### M6 Stage Order

```text
M6A Supplier Core
-> M6B Model Catalog And Binding
-> M6C Adapter Cutover
-> M6D Management UI
-> M6E Migration And Acceptance
```

Stages may be planned together but are implemented and reviewed separately. A later stage may not begin until the preceding stage is merged or an approved execution contract explicitly allows an isolated dependency branch.

### M6 Planning And Execution Rules

- Planning may modify only `AGENTS.md`, M6 specs, and M6 plans.
- Implementation uses TDD and one focused commit per independently reviewable task.
- Only the main agent writes. Subagents are read-only unless an approved stage contract explicitly says otherwise.
- Default Python, Node, browser, worker, verifier, and migration tests must deny unexpected real network access.
- Supplier management APIs remain loopback-only at the application layer.
- Secrets, signed URLs, provider responses containing secrets, databases, `runtime-data`, and private generation results must never enter Git.
- Existing M1-M5 behavior remains the regression baseline.
- Every stage must preserve its documented rollback point.

### M6 Branch Roles

```text
docs/provider-model-management-design
-> approved design, M6 governance, and M6A-M6E plans only

feat/m6a-supplier-core
feat/m6b-model-catalog-binding
feat/m6c-adapter-cutover
feat/m6d-management-ui
feat/m6e-migration-acceptance
-> one implementation stage per branch

main
-> protected integration branch
```

### M6 Completion Tokens

```text
M6_GOVERNANCE_AND_PLANS_READY_FOR_REVIEW
M6_GOVERNANCE_AND_PLANS_BLOCKED
M6A_READY_FOR_REVIEW
M6B_READY_FOR_REVIEW
M6C_READY_FOR_REVIEW
M6D_READY_FOR_REVIEW
M6E_READY_FOR_REVIEW
M6_COMPLETE
```

---

## Historical Baseline

The following milestones are complete and must be preserved as implementation baseline:

```text
Milestone 1 — Web workflow baseline
Milestone 2 — Assets, prompts, and shot prompt baseline
Milestone 3 — Agnes Video Generation, Persistent Jobs, Results, and Rerun
Milestone 4 — Mock-provider chapter rehearsal, reporting, runbook, and read-only UI visibility
```

M3, M4, and M5 are no longer active milestones. Their implementation, tests, verifiers, real-provider evidence, and documented safety rules remain binding baseline.

Do not regress:

* M1 web workflow behavior;
* M2 asset and shot prompt behavior;
* M3 generation jobs, result persistence, rerun, poller, provider abstraction, asset delivery, and results UI;
* M4 mock-provider chapter rehearsal verifier;
* M4 JSON/Markdown report;
* M4 rehearsal runbook;
* M4 UI visibility plan;
* M4 Phase 1 read-only rehearsal visibility panel;
* M5 real Agnes provider integration, public asset delivery, long-running gateway, and reboot recovery.

## Historical M5 Governance

The remaining M5 sections below are retained as historical safety baseline for the completed real-provider integration. They do not override the active M6 scope, stage order, branch roles, completion tokens, or default real-network denial defined above and in the M6 governance contract.

---

## Authority Order

Before any M5 design, planning, implementation, testing, review, commit, or push, read the relevant documents in this order:

1. `AGENTS.md` current M5 rules.
2. `docs/milestones/m4-final-closeout.md`
3. `docs/milestones/m3-baseline-summary.md`
4. `docs/milestones/m3-real-provider-readiness.md`
5. `docs/milestones/m4-rehearsal-runbook.md`
6. `docs/milestones/m4-ui-visibility-plan.md`
7. `docs/milestones/m5-readiness-plan.md` after it is approved.
8. Current runtime, provider, Web, and test implementation:

   * `ai_drama_runtime/`
   * `ai_drama_web/`
   * `web/`
   * `tests/`
   * `tools/`
   * `migration/`
9. Current official Agnes Video documentation.
10. Secondary Agnes support material only:

* `https://github.com/lj1270998580-crypto/Agnes-help-skill`

When documents conflict, apply this priority:

```text
M5 safety gate
→ M4 final closeout
→ M3 baseline
→ approved M5 readiness plan
→ current implementation
→ current official Agnes Video documentation
→ secondary Agnes material
```

Official Agnes documentation may update the provider contract only after the conflict is explicitly reported and reviewed. Do not silently change the provider contract.

---

## Branch Roles

Use these branch roles:

```text
docs/m5-agents-governance
→ AGENTS.md governance alignment only

docs/m5-readiness-plan
→ M5 readiness plan, checklist, dry-run design, and smoke-test gate documentation only

feat/m5-real-provider-smoke-test
→ future real smoke-test implementation only after readiness plan approval and explicit user authorization

main
→ protected integration branch
```

Do not implement real provider execution on documentation branches.

Do not merge to `main` unless the user explicitly requests final merge after review.

Do not force push.

Do not squash unless explicitly requested.

Prefer fast-forward merges for approved milestone branches.

---

## M5 Authorization Gate

### Without Real Smoke-Test Authorization

Before the user sends:

```text
AUTHORIZE_REAL_AGNES_VIDEO_SMOKE_TEST
```

agents may only:

* inspect repository files;
* read specifications, plans, code, tests, and docs;
* run existing tests, builds, verifiers, and dry-run checks;
* prepare M5 readiness documentation;
* prepare readiness checklist;
* inspect environment-variable presence without exposing values;
* verify LocalSecretStore presence without printing secrets;
* verify public URL validation logic;
* verify signed asset URL construction logic in dry-run mode;
* prepare final review reports.

Before authorization, agents must not:

* submit an Agnes video request;
* poll a real Agnes job;
* download a real Agnes result;
* create a real provider execution script that can run by default;
* configure or print a real API key;
* expose any secret to browser, logs, artifacts, reports, exceptions, or Git history;
* bypass public HTTPS asset checks;
* run batch provider requests;
* run retries beyond an explicitly authorized single smoke request.

### With Real Smoke-Test Authorization

The token:

```text
AUTHORIZE_REAL_AGNES_VIDEO_SMOKE_TEST
```

authorizes at most one controlled real Agnes smoke test, and only if the readiness checklist is already GO.

The agent must still stop if any readiness item is NO-GO.

Authorization does not permit:

* batch production;
* full chapter production;
* unlimited retries;
* provider abstraction rewrite;
* database schema expansion;
* LibTV execution;
* subtitles, BGM, final timeline, or export work.

---

## M5 Multi-Agent Collaboration Rules

Use multi-agent review for M5 planning and readiness work.

Required roles:

### Product Agent

Responsibilities:

* define M5 product goal;
* define user acceptance criteria;
* define what “real smoke test passed” means;
* confirm M5 does not imply full production launch.

Required output:

* findings;
* risks;
* checklist items;
* go / no-go criteria.

### Backend Agent

Responsibilities:

* inspect existing Agnes provider implementation;
* inspect generation execution service;
* inspect poller behavior;
* inspect result persistence;
* inspect result content endpoint;
* inspect asset delivery service;
* inspect provider parameter allowlist;
* inspect duration mapping.

Required output:

* findings;
* risks;
* checklist items;
* go / no-go criteria.

### Ops Agent

Responsibilities:

* inspect environment variable requirements;
* inspect public HTTPS requirements;
* inspect `AI_DRAMA_PUBLIC_BASE_URL`;
* inspect rate-limit settings;
* inspect rollback and cleanup requirements;
* inspect operator runbook requirements.

Required output:

* findings;
* risks;
* checklist items;
* go / no-go criteria.

### QA Agent

Responsibilities:

* design readiness checklist;
* design dry-run verification;
* design failure categories;
* design regression commands;
* verify that default tests do not make real provider requests.

Required output:

* findings;
* risks;
* checklist items;
* go / no-go criteria.

### Security Agent

Responsibilities:

* inspect `LocalSecretStore`;
* inspect settings endpoint behavior;
* inspect secret redaction;
* inspect signed URL safety;
* inspect log/report/artifact leakage risks;
* inspect safety grep results.

Required output:

* findings;
* risks;
* checklist items;
* go / no-go criteria.

### Orchestrator

Responsibilities:

* coordinate agents;
* resolve conflicts;
* integrate findings;
* produce final M5 readiness decision;
* ensure no real request is made without authorization.

Only the main agent may commit.

Subagents are read-only unless explicitly authorized.

No subagent may execute a real Agnes request.

No subagent may expose secrets.

---

## M5 Scope

M5 is in scope for:

* real provider readiness checklist;
* public HTTPS asset delivery readiness;
* Agnes API key readiness;
* runtime provider switching readiness;
* signed asset URL reachability check;
* dry-run safety verification;
* one-shot real smoke-test gate design;
* expected success evidence design;
* failure classification;
* rollback and cleanup guidance;
* report separation between mock evidence and real provider evidence;
* operator go / no-go decision template.

M5 may prepare a plan for a future authorized smoke test.

M5 may not execute the real smoke test until explicitly authorized.

---

## M5 Non-Scope

M5 is not in scope for:

* automatic real Agnes request without authorization;
* batch production;
* full chapter production;
* video quality benchmark;
* LibTV execution;
* dubbing;
* subtitles;
* BGM;
* sound effects;
* timeline editing;
* video trimming;
* video concatenation;
* transitions;
* color grading;
* final episode export;
* publishing;
* multi-user authentication or permissions;
* collaboration;
* generic workflow engines;
* generic Agent runtimes;
* provider plugin marketplace;
* provider abstraction rewrite;
* distributed queues;
* Redis;
* Celery;
* Kubernetes;
* PostgreSQL migration;
* database schema expansion unless separately approved later;
* production launch.

Documentation may mention later work, but no later-milestone implementation may be added during M5 readiness planning.

---

## M5 Readiness Checklist Requirements

The approved M5 readiness plan must contain a checklist covering at least the following areas.

### Repository Readiness

Required checks:

* `main` is clean;
* M3 verifier passes;
* M4 verifier passes;
* Python tests pass;
* Web tests pass;
* Web build passes;
* Web e2e passes;
* migration verifier passes;
* `git diff --check` passes.

### Environment Readiness

Required checks:

* `AI_DRAMA_RUNTIME_PROVIDER=agnes`;
* `AI_DRAMA_PUBLIC_BASE_URL` configured;
* `AI_DRAMA_PUBLIC_BASE_URL` uses HTTPS;
* `AI_DRAMA_PUBLIC_BASE_URL` is not localhost;
* `AI_DRAMA_PUBLIC_BASE_URL` is not loopback;
* `AI_DRAMA_PUBLIC_BASE_URL` is not private IP;
* `AI_DRAMA_PUBLIC_BASE_URL` is not a file path;
* `AI_DRAMA_PUBLIC_BASE_URL` has no userinfo;
* `AI_DRAMA_AGNES_VIDEO_RPM` is configured and sane;
* `AI_DRAMA_AGNES_POLL_INTERVAL_SECONDS` is configured and sane.

### Secret Readiness

Required checks:

* Agnes API key exists in `LocalSecretStore`;
* API key is never printed;
* API key is never committed;
* API key is never returned to browser;
* settings endpoint reports configured/unconfigured status only;
* logs redact Authorization headers and API-key-like fields;
* reports do not contain secret values.

### Public Asset Readiness

Required checks:

* signed asset URL can be generated;
* signed asset URL is HTTPS;
* signed asset URL rejects invalid signature;
* signed asset URL rejects expired signature;
* signed asset URL rejects non-image assets;
* signed asset URL does not contain Agnes API key;
* referenced image asset is externally reachable before real provider submission;
* localhost, loopback, private IP, local file paths, and userinfo are rejected for real submissions.

### Provider Readiness

Required checks:

* provider uses explicit video status/result path;
* provider does not silently substitute `task_id` for `video_id`;
* duration mapping uses:

  * 5 seconds → 121 frames, 24 fps;
  * 10 seconds → 241 frames, 24 fps;
* provider params allowlist remains strict;
* canonical request stores asset IDs, not temporary signed URLs;
* local result persistence is enabled;
* provider result bytes are downloaded and stored locally;
* previous results are retained;
* current result selection is explicit;
* poller handles:

  * queued;
  * submitting;
  * submitted;
  * polling;
  * completed;
  * failed;
  * cancelled;
  * submission outcome unknown.

### Safety Readiness

Required checks:

* dry-run mode makes no real Agnes request;
* real smoke test requires exact token:
  `AUTHORIZE_REAL_AGNES_VIDEO_SMOKE_TEST`;
* no retries beyond approved single smoke request;
* no default test calls real Agnes;
* no CI job calls real Agnes by default;
* no API key leakage;
* generated report separates mock evidence from real provider evidence.

---

## M5 Smoke Test Scenario

The minimum real smoke test scenario must be planned as follows, but not executed without authorization.

Input:

```text
one existing usable image asset
one short video generation job
duration_seconds = 5
provider = agnes
one idempotency key
one shot id
```

Expected flow:

```text
create signed asset URL
verify signed asset URL is externally reachable
submit Agnes video request
receive provider job/video id
persist internal generation job id
poll provider status
receive completed URL or failed status
download mp4 if completed
persist local result bytes
persist result metadata
expose /api/results/{result_id}/content
show result in existing generation results UI
show evidence in M4.3 visibility panel
write smoke test report
```

The real smoke test must be one-shot unless the user separately authorizes another attempt.

---

## Expected Success Evidence

A successful M5 smoke test must produce evidence including:

* provider job id / video id;
* internal generation job id;
* result id;
* local object id;
* local content URL;
* poll status timeline;
* downloaded mp4 byte size;
* result selection state;
* no secret leakage confirmation;
* report path;
* UI visibility confirmation;
* explicit statement that this was a single authorized real provider smoke test.

The report must separate:

```text
mock M4 rehearsal evidence
real M5 smoke-test evidence
```

---

## Failure Categories

M5 readiness and smoke-test reporting must classify failures using these categories:

```text
missing_api_key
invalid_public_base_url
input_asset_unreachable
provider_submit_failed
provider_poll_failed
provider_failed
provider_timeout
result_download_failed
local_persistence_failed
ui_visibility_failed
secret_leak_detected
unexpected_real_request
unknown
```

Each category must define:

* meaning;
* operator action;
* whether retry is allowed;
* whether user authorization is required again.

Default retry rule:

```text
Any new real provider submission requires explicit user authorization again unless the approved smoke-test plan says otherwise.
```

---

## Secret and Security Rules

* Read the Agnes API key only through `LocalSecretStore`.
* Never accept Agnes API key in generation request bodies.
* Never return the full key to browser.
* Never write the key to logs.
* Never write the key to artifacts.
* Never write the key to provider metadata.
* Never write the key to test snapshots.
* Never write the key to exceptions.
* Never write the key to exported bundles.
* Never write the key to Git history.
* Sanitize Authorization headers.
* Sanitize API-key fields.
* Sanitize token-like strings.
* Signed public asset URLs must not contain provider secrets.
* Use constant-time comparison for signatures.
* Real provider tests must be explicit opt-in.
* Default test suites must use fake provider or mocked Agnes HTTP contracts.

---

## Static Safety Checks

M5 planning and readiness review must include safety grep:

```bash
grep -RniE 'apihub.agnes-ai.com|AUTHORIZE_REAL_AGNES_VIDEO_SMOKE_TEST|AI_DRAMA_PUBLIC_BASE_URL|LocalSecretStore|AgnesImageBackend' \
  docs tools tests ai_drama_web web/src
```

Allowed hits:

* docs/readiness checklist;
* existing Agnes provider implementation;
* settings UI/backend;
* test mocks/assertions;
* deferred-token docs/UI copy.

Disallowed hits:

* new unguarded real Agnes execution;
* API key printed to logs;
* API key committed;
* real request path outside explicit authorization;
* browser path that directly calls real Agnes.

---

## Stop Conditions

Stop and report instead of improvising when:

* the user has not sent `AUTHORIZE_REAL_AGNES_VIDEO_SMOKE_TEST` and a real request would be needed;
* `AI_DRAMA_PUBLIC_BASE_URL` is missing;
* public base URL is not HTTPS;
* public base URL is localhost, loopback, private IP, file path, or contains userinfo;
* Agnes API key is missing;
* Agnes API key would be exposed to browser, logs, artifacts, reports, exceptions, or Git history;
* signed asset URL cannot be externally reached;
* official Agnes Video documentation conflicts with current implementation;
* provider does not return a stable queryable video identifier;
* provider requires an input mode unsupported by current M3/M4 implementation;
* real request would require unapproved retries;
* real request would require batch execution;
* any safety grep finds a new unguarded real provider path;
* baseline M3/M4 tests fail for unrelated reasons;
* a proposed change requires provider abstraction rewrite;
* a proposed change requires database schema expansion not separately approved;
* a proposed change requires LibTV, subtitles, BGM, final timeline, or production export;
* a secret would need to be exposed to proceed.

Do not commit or push partial work after a Stop Condition unless the user explicitly instructs a documentation-only blocked report.

---

## Testing and Development Rules

Use test-driven development for any implementation work after readiness planning.

For every implementation task:

1. write the focused failing test;
2. run it and confirm expected failure;
3. implement the minimum code required;
4. run focused tests;
5. run affected regression tests;
6. perform specification-compliance review;
7. perform code-quality review;
8. fix findings;
9. rerun focused and affected tests;
10. create one focused commit;
11. continue to the next task only after the current task passes.

Do not weaken tests.

Do not skip tests merely to pass.

Do not delete acceptance checks.

Do not rewrite golden outputs without explicit justification.

Do not let real provider tests run by default.

---

## M5 Verification Baseline

For M5 planning/readiness work, run at minimum:

```bash
python3 tools/verify_m4_chapter_rehearsal.py
python3 tools/verify_m3_agnes_generation.py
python3 -m pytest -q
npm --prefix web run test -- --run
npm --prefix web run build
npm --prefix web run test:e2e
python3 migration/tools/verify_migration.py
git diff --check
```

If M5 only changes documentation, focused document validation plus `git diff --check` may be enough, but the final report must say which verification was run and why broader tests were or were not run.

Before any real smoke-test implementation or execution, rerun the full verification baseline.

---

## ChatGPT Review Handoff Policy

Whenever a design, implementation plan, report, specification, or code change needs to be handed to ChatGPT for review, Codex must follow this policy unless the artifact contains sensitive information:

1. Save the file inside the current Git repository, not only under `/tmp` or an external worktree path.
2. When the artifact is complete, automatically run `git add`, commit it, and push the current working branch to `origin`.
3. Do not wait for the user to request a push again.
4. The final response must include:
   - repository;
   - branch;
   - commit SHA;
   - repository-relative file path;
   - PR URL or branch compare URL.
5. If the branch does not yet exist on the remote, automatically run:

   ```bash
   git push -u origin <current-branch>
   ```

6. If `gh` is authenticated, automatically create or update the PR. If `gh` is not authenticated, provide a compare URL instead.
7. Never commit API keys, bearer credentials, tokens, signed URLs, passwords, `runtime-data`, databases, or private generation results.
8. If the file contains sensitive information, generate a redacted review copy, commit and push only that copy, and explicitly state that the original file was not uploaded.
9. After ChatGPT review, continue updating, committing, and pushing on the same branch. Do not create an unnecessary new branch.
10. Pause only when push permission, login, 2FA, or a sensitive-information decision requires user intervention. Use exactly:

    ```text
    USER_ACTION_REQUIRED
    ACTION=<the one required action>
    REASON=<one-sentence reason>
    RESUME_WITH=<short phrase to reply after completion>
    ```

For qualifying ChatGPT review handoffs, this section is standing publication authorization and satisfies the general requirement below that a user explicitly authorize a push.

### Required Review Handoff Format

Use this machine-readable handoff block:

```text
REVIEW_HANDOFF_READY
REPOSITORY=Java-zengzhiwen/ai-drama
BRANCH=<current-branch>
COMMIT=<commit-sha>
FILE=<repository-relative-file-path>
PR_URL=<url-or-NONE>
```

### Temporary And External Reports

When a review artifact initially exists only under `/tmp` or outside the repository, create a redacted archival review copy under an appropriate repository path such as:

```text
docs/reports/
docs/reviews/
artifacts/reports/
```

Commit and push the archival copy using the same handoff policy. Do not upload the sensitive original.

---

## Commit and Push Rules

* Keep one focused commit per task.
* Do not combine unrelated M5 work into a single commit.
* Do not amend or rewrite historical M1/M2/M3/M4 commits.
* Do not push unless the user explicitly authorizes publication.
* Do not merge to `main` without user approval.
* Prefer fast-forward merges after review.
* Do not force push.
* Do not squash unless the user explicitly requests it.
* Do not delete milestone branches until the user approves cleanup.

---

## Go / No-Go Decision Template

M5 readiness reports must include:

```text
M5 Readiness Decision:
- Repository readiness: GO / NO-GO
- Environment readiness: GO / NO-GO
- Secret readiness: GO / NO-GO
- Public asset readiness: GO / NO-GO
- Provider readiness: GO / NO-GO
- Safety readiness: GO / NO-GO

Overall:
- M5_REAL_PROVIDER_SMOKE_TEST_READY
or
- M5_REAL_PROVIDER_SMOKE_TEST_NOT_READY

Reason:
...

Required fixes:
...
```

No real Agnes smoke test may run unless the overall decision is:

```text
M5_REAL_PROVIDER_SMOKE_TEST_READY
```

and the user separately provides:

```text
AUTHORIZE_REAL_AGNES_VIDEO_SMOKE_TEST
```

---

## Completion Tokens

Allowed M5 governance and readiness tokens:

```text
M5_AGENTS_GOVERNANCE_READY_FOR_REVIEW
M5_AGENTS_GOVERNANCE_BLOCKED
M5_READINESS_PLAN_READY_FOR_REVIEW
M5_READINESS_PLAN_BLOCKED
M5_REAL_PROVIDER_SMOKE_TEST_READY
M5_REAL_PROVIDER_SMOKE_TEST_NOT_READY
M5_REAL_PROVIDER_SMOKE_TEST_READY_FOR_REVIEW
M5_REAL_PROVIDER_SMOKE_TEST_BLOCKED
M5_REAL_PROVIDER_SMOKE_TEST_COMPLETE
M5_REAL_PROVIDER_SMOKE_TEST_FAILED
```

Do not use `M3_COMPLETE` as the active milestone completion token.

M3 remains historical baseline only.

M4 remains closed historical baseline only.

---

## M5 Planning Completion

Only declare M5 readiness planning complete when:

* `docs/milestones/m5-readiness-plan.md` exists;
* multi-agent review is included;
* readiness checklist is included;
* environment requirements are included;
* secret management requirements are included;
* public asset delivery requirements are included;
* real smoke-test gate is included;
* smoke-test scenario is included;
* expected evidence is included;
* failure categories are included;
* safety rules are included;
* verification commands are included;
* go / no-go template is included;
* user acceptance gate is included;
* no real Agnes request was made;
* working tree is clean.

Final status for readiness planning must be exactly one of:

```text
M5_READINESS_PLAN_READY_FOR_REVIEW
M5_READINESS_PLAN_BLOCKED
```

---

## M5 Real Smoke-Test Completion

Only declare a real provider smoke test complete when:

* readiness decision was GO;
* user explicitly provided `AUTHORIZE_REAL_AGNES_VIDEO_SMOKE_TEST`;
* exactly one authorized real Agnes smoke request was submitted;
* provider job/video id was recorded;
* polling timeline was recorded;
* result was either completed and locally persisted, or failed with classified failure;
* no secret leaked;
* report separates real provider evidence from mock evidence;
* UI visibility was checked if a result exists;
* working tree is clean or changes are explicitly reported.

Final status for real smoke testing must be exactly one of:

```text
M5_REAL_PROVIDER_SMOKE_TEST_COMPLETE
M5_REAL_PROVIDER_SMOKE_TEST_FAILED
M5_REAL_PROVIDER_SMOKE_TEST_BLOCKED
```
