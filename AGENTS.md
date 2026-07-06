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

## AI Drama Web Production MVP — Milestone 2

Milestone 1 is complete and is the required implementation baseline.

The active product milestone is:

```text
Milestone 2 — Production Profiles, Visual Assets, Asset Requirements,
Agnes Image Generation, and Shot Prompt Studio
```

### Authority Order

Before any Milestone 2 design, planning, implementation, testing, review,
commit, or push, read the following documents in full:

1. Product scope authority:

   `docs/superpowers/specs/2026-07-05-ai-drama-web-production-mvp-design-v2.md`

2. Program and milestone sequencing authority:

   `docs/superpowers/plans/2026-07-05-ai-drama-web-production-mvp-implementation-program.md`

3. Current implementation authority:

   `docs/superpowers/plans/2026-07-05-m2-assets-shot-prompt-studio.md`

4. Existing visual-system baseline:

   `docs/product-design/m1/`

5. Milestone 2 Product Design authority, after it is approved:

   `docs/product-design/m2/`

When documents conflict, apply this priority:

```text
MVP Design Spec
→ M2 Implementation Plan
→ approved M2 Product Design handoff
→ existing runtime contracts and tests
→ current Agnes official API documentation
→ Agnes Help Skill as secondary guidance
```

Product Design documents control page layout, interaction, component behavior,
screen states, and visual continuity. They do not override runtime, persistence,
gate, provenance, or provider-integration architecture.

### Branches

Use these branch roles:

```text
docs/m2-product-design
→ M2 Product Design documents and prototype evidence only

feat/mvp-assets-shot-prompts
→ M2 production implementation only
```

Do not implement production code on `docs/m2-product-design`.

Do not perform open-ended Product Design exploration on
`feat/mvp-assets-shot-prompts`.

### Product Design Gate

Before any Milestone 2 production implementation, all of the following must
exist and be approved:

- `docs/product-design/m2/brief.md`
- `docs/product-design/m2/information-architecture.md`
- `docs/product-design/m2/workflow-map.md`
- `docs/product-design/m2/interaction-spec.md`
- `docs/product-design/m2/screen-states.md`
- `docs/product-design/m2/component-inventory.md`
- `docs/product-design/m2/visual-tokens.md`
- `docs/product-design/m2/selected-direction.md`
- `docs/product-design/m2/implementation-handoff.md`

`selected-direction.md` must identify exactly one approved direction.

`implementation-handoff.md` must define:

- routes and tab structure;
- primary page components;
- API data dependencies;
- loading, empty, normal, blocked, generating, failed, usable, rejected,
  ready, and needs-revision states;
- gate and disabled-action behavior;
- responsive behavior;
- reusable Milestone 1 components;
- design decisions the implementation agent must not change.

If these files are missing, incomplete, or unapproved:

- do not write Milestone 2 business code;
- do not infer a final UI from the implementation plan;
- output `M2_PREFLIGHT_BLOCKED_BY_DESIGN`;
- stop and request completion or approval of the M2 Product Design package.

### Authorization Gate

Before the user sends:

```text
AUTHORIZE_M2_IMPLEMENTATION
```

the agent may only:

- inspect the repository;
- read specifications, plans, code, tests, and design files;
- install existing declared dependencies to establish a baseline;
- run tests, builds, verifiers, and read-only analysis;
- prepare and report a Milestone 2 Preflight;
- work on the dedicated Product Design documentation branch when explicitly
  instructed to perform the M2 Product Design Sprint.

Before authorization, do not:

- create or alter production database tables;
- modify runtime, API, or production frontend code;
- add the Shot Prompt Skill package;
- call Agnes;
- create implementation commits.

A valid implementation preflight must end with exactly one of:

```text
M2_PREFLIGHT_READY
M2_PREFLIGHT_BLOCKED
M2_PREFLIGHT_BLOCKED_BY_DESIGN
```

Only `M2_PREFLIGHT_READY` followed by the explicit authorization token permits
production implementation.

### Milestone 2 In Scope

Implement only the Milestone 2 plan:

#### Production Profiles

- `CharacterProfile`
- `SceneProfile`
- `PropProfile`
- `StyleProfile`
- profile create, read, update, list, and delete behavior;
- strict payload validation;
- chapter and project scoping;
- reference-asset bindings;
- continuity, costume, scene-layout, lighting, and style notes.

#### Asset Studio

- local image upload;
- immutable object storage;
- asset metadata and classification;
- preview;
- asset versions;
- bindings to characters, scenes, props, and shots;
- usable, rejected, generating, and failed states;
- current selected asset;
- Agnes text-to-image and image-to-image generation.

Supported asset types are limited to:

```text
character_reference
character_outfit
scene_reference
scene_angle
prop_reference
shot_keyframe
```

#### Asset Requirement Analysis

- derive requirements from the current approved Canonical Storyboard;
- identify missing character, costume, scene, scene-angle, prop, and keyframe
  assets;
- expose per-shot readiness;
- support these product states:

```text
ready
missing_assets
asset_generation_in_progress
asset_review_required
```

#### Shot Prompt Studio

Use this boundary:

```text
Shot Prompt Skill
→ creative transformation and canonical prompt content

ShotPromptService
→ gates, input assembly, persistence, validation, asset binding,
  revision management, readiness, and API behavior
```

The prompt workflow must support:

- one prompt unit per Canonical Storyboard shot;
- chapter-wide generation;
- single-shot regeneration;
- immutable manual revisions;
- positive prompt;
- negative prompt;
- continuity notes;
- asset references;
- Agnes video-parameter preview only;
- prompt history;
- states:

```text
draft
blocked_by_assets
ready
needs_revision
```

Milestone 2 may prepare provider-neutral prompt data for later video
generation, but it must not submit video jobs.

### Milestone 2 Out of Scope

Do not implement:

- Agnes video generation;
- video job state machines;
- video polling;
- video results;
- video rerun;
- `LibTVBackend` or LibTV execution;
- dubbing;
- subtitles;
- BGM;
- sound effects;
- video editing or final export;
- multi-user authentication or permissions;
- generic workflow engines;
- generic Agent runtimes;
- provider plugin marketplaces;
- PostgreSQL;
- Redis;
- distributed queues;
- microservices;
- Kubernetes;
- historical Phase 3B–3E governance, qualification, or verifier expansion.

Navigation labels for later milestones may remain visible and locked, but no
later-milestone implementation may be added.

### Existing Behavior That Must Be Preserved

Preserve all Milestone 1 and historical runtime behavior:

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
- script and storyboard Web APIs;
- M1 Web workspace and gates.

Do not duplicate existing runtime logic inside FastAPI routers or React
components.

### Persistence Rules

- Product tables must be additive.
- Do not destructively rewrite historical tables.
- Use the existing SQLite database and object store.
- Large JSON, uploaded images, provider request bodies, and provider responses
  belong in immutable object storage when the implementation plan requires it.
- Store hashes and object identifiers in relational rows.
- Preserve referential integrity and project/chapter scoping.
- Migrations must remain compatible with existing migration preview and
  current-version checks.
- A rerun of migrations must be idempotent.

### Agnes Image Integration Rules

Agnes API behavior must be verified against the current official Agnes
documentation during implementation.

The only approved secondary support source is:

`https://github.com/lj1270998580-crypto/Agnes-help-skill`

Do not use unrelated community Agnes skills as implementation authority.

Current expected image integration baseline:

- endpoint: `POST https://apihub.agnes-ai.com/v1/images/generations`;
- model: `agnes-image-2.1-flash`;
- text-to-image uses `model`, `prompt`, and `size`;
- image-to-image inputs belong in `extra_body.image`;
- local images should use Data URI/Base64 where supported;
- `response_format` belongs in `extra_body` when requested;
- API keys remain server-side and must never be returned to the browser,
  stored in generated artifacts, or written to logs.

If current official documentation conflicts with this baseline, stop and report
the exact conflict before changing the contract.

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
9. create one focused commit;
10. continue to the next task.

Do not weaken, skip, delete, or rewrite existing tests merely to make a change
pass.

Keep implementation aligned with the exact task order in:

`docs/superpowers/plans/2026-07-05-m2-assets-shot-prompt-studio.md`

### Agent Collaboration Rules

- Use subagent-driven development after authorization.
- The main agent coordinates, reviews, integrates, and owns final decisions.
- At most one code-writing implementer may operate at a time.
- Read-only exploration, test analysis, and review agents may run in parallel.
- Subagents must receive the current task scope and forbidden-scope list.
- Do not allow multiple write agents to modify overlapping files.
- Do not begin the next task until the current task has passed focused tests,
  review, and commit.

### Commit and Push Rules

- Keep one focused commit per implementation task.
- Do not combine all Milestone 2 work into a single commit.
- Do not amend or rewrite historical Milestone 1 commits.
- Do not push unless the user explicitly authorizes publication.
- Do not merge to `main`.
- Do not begin Milestone 3 after Milestone 2 completion.

### Stop Conditions

Stop and report instead of improvising when:

- required M2 Product Design files are missing or not approved;
- the selected design direction is ambiguous;
- current official Agnes documentation conflicts with the planned API contract;
- a required migration would destructively alter historical data;
- the current branch does not contain the complete Milestone 1 baseline;
- baseline tests fail for reasons unrelated to the current task;
- the implementation plan conflicts materially with the approved MVP Design;
- a proposed change requires Agnes video, LibTV, post-production, distributed
  infrastructure, or another later-milestone capability;
- a secret would need to be exposed to the browser or committed to the
  repository.

Do not commit or push partial work after a Stop Condition.

### Milestone 2 Verification

Before declaring completion, run all verification commands required by the M2
implementation plan, including at minimum:

```bash
python3 migration/tools/verify_migration.py
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q
npm --prefix web run test -- --run
npm --prefix web run build
npm --prefix web run test:e2e
```

Also run the Milestone 1 verifier and the Milestone 2 verifier introduced by
the implementation plan.

Browser or Playwright verification must cover:

- profile creation and editing;
- asset upload and preview;
- asset binding;
- Agnes image fake-backend flow;
- asset requirement states;
- chapter-wide Shot Prompt generation;
- single-shot prompt editing or regeneration;
- prompt blocked-by-assets and ready transitions;
- Milestone 3 navigation remaining locked.

### Completion Status

Only declare Milestone 2 complete when:

- all M2 implementation-plan tasks are complete;
- all focused and regression tests pass;
- migration verification passes;
- the M1 verifier still passes;
- the M2 verifier passes;
- frontend tests and build pass;
- M2 E2E and Browser QA pass;
- the working tree is clean;
- no Milestone 3 scope was implemented.

The final status must be exactly one of:

```text
M2_COMPLETE
M2_BLOCKED
M2_FAILED
```

After `M2_COMPLETE`, stop. Do not start Milestone 3.
