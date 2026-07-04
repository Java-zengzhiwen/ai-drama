# AI Drama Web Production MVP Implementation Program

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the approved local, single-user Web MVP that turns one novel chapter into traceable Agnes-generated video clips with asset, prompt, result, and rerun workflows.

**Architecture:** Keep the existing Python runtime as the domain execution core. Add a FastAPI application layer, a React/TypeScript Web client, product-domain persistence on the existing SQLite database, a focused Shot Prompt Skill, and a persistent Agnes generation worker. Deliver through four sequential milestones; each milestone must merge before the next starts.

**Tech Stack:** Python 3.11, existing `ai_drama_runtime`, FastAPI, Pydantic v2, SQLite, local content-addressed object storage, HTTPX, React, TypeScript, Vite, TanStack Query, React Router, Vitest, Playwright.

---

## 1. Authoritative documents

Implementation must read these files before any code change:

- `AGENTS.md`
- `docs/superpowers/specs/2026-07-05-ai-drama-web-production-mvp-design-v2.md`
- this program plan
- the current milestone plan

The approved MVP design overrides the historical Phase 3B–3E program. Existing Phase 1, Phase 2, and Phase 3A code remains part of the baseline.

## 2. Program branch and merge strategy

Implement one milestone per branch and pull request:

```text
feat/mvp-web-workflow
feat/mvp-assets-shot-prompts
feat/mvp-agnes-generation
test/mvp-real-chapter-acceptance
```

Rules:

1. Create each branch from the latest merged `main`.
2. Use an isolated worktree for each milestone.
3. Do not develop two writable milestones in parallel.
4. Merge only after focused tests, full Python regressions, frontend tests, changed-file review, and a clean worktree.
5. Do not squash away evidence needed to understand schema or migration changes unless the user explicitly requests squash merges.

## 3. Plan decomposition

| Order | Plan | User-visible outcome |
|---|---|---|
| 1 | `2026-07-05-m1-web-script-storyboard-workbench.md` | Project, chapter, script, and storyboard flow works in Web UI |
| 2 | `2026-07-05-m2-assets-shot-prompt-studio.md` | Profiles, assets, asset requirements, and editable Shot Prompts work |
| 3 | `2026-07-05-m3-agnes-generation-results-rerun.md` | Agnes image/video jobs, polling, results, errors, and reruns work |
| 4 | `2026-07-05-m4-real-chapter-mvp-acceptance.md` | A real 12–20 shot chapter completes the MVP acceptance flow |

## 4. Global file structure

```text
ai_drama_runtime/                 # existing runtime; extend narrowly
ai_drama_web/                     # new FastAPI product/application package
  app.py
  config.py
  dependencies.py
  errors.py
  store.py
  schemas/
  routers/
  services/
  providers/
  jobs/
web/                              # React/TypeScript client
  package.json
  vite.config.ts
  src/
  tests/
skills/
  ai-drama-shot-prompt-skill/
    v0.1.0/
tests/
  web/
  providers/
  integration/
acceptance/
  web-mvp-chapter-001/
docs/superpowers/specs/
docs/superpowers/plans/
```

No generic plugin framework, workflow DSL, multi-user subsystem, post-production subsystem, Redis, or PostgreSQL is added.

## 5. Cross-milestone contracts

### 5.1 Existing runtime remains authoritative for

```text
Artifact
Revision
ValidatorResult
ApprovalRecord
RevisionDependency
RevisionOutput
InputSnapshot
content-addressed object storage
```

### 5.2 Product persistence owns

```text
Project
Chapter
ChapterSourceRevision
ProductionProfile
AssetRecord
AssetBinding
AssetRequirementSet
GenerationJob
GenerationResult
ShotResultSelection
RerunRecord
```

### 5.3 Skill/Service boundary

```text
Skill: creates creative content
Service: enforces gates, assembles inputs, persists revisions, validates, and exposes APIs
```

### 5.4 Provider boundary

```python
class GenerationBackend(Protocol):
    def create_image_job(self, request: "ImageGenerationRequest") -> "ProviderJob": ...
    def create_video_job(self, request: "VideoGenerationRequest") -> "ProviderJob": ...
    def get_job_status(self, provider_job_id: str) -> "ProviderJobStatus": ...
    def fetch_result(self, provider_job_id: str) -> "ProviderResult": ...
```

MVP implements only `AgnesBackend`. Agnes credentials are configured through the Web settings page and stored only by the server-side local secret store.

## 6. Program verification gate

Run at every milestone completion:

```bash
python3 migration/tools/verify_migration.py
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q
npm --prefix web run test -- --run
npm --prefix web run build
```

From Milestone 3 onward also run:

```bash
python3 -m pytest -q tests/providers tests/integration/test_generation_recovery.py
```

From Milestone 4 onward also run:

```bash
python3 tools/verify_web_mvp_acceptance.py \
  --data-root /tmp/ai-drama-web-mvp-acceptance \
  --acceptance-root acceptance/web-mvp-chapter-001
```

Expected final status:

```text
AI_DRAMA_WEB_PRODUCTION_MVP_COMPLETE
AGNES_BACKEND_OPERATIONAL
LIBTV_DEFERRED
POST_PRODUCTION_DEFERRED
```

## 7. Stop conditions

Stop implementation and return to the user when any of these occurs:

- the approved design requires a new independent subsystem not represented in the four milestone plans;
- current runtime behavior contradicts the design and cannot be wrapped without changing existing acceptance semantics;
- Agnes official API behavior conflicts with the planned request or polling contract;
- a migration cannot preserve all current rows and foreign-key validity;
- existing Script or Storyboard regressions cannot be restored without weakening tests;
- a proposed fix introduces LibTV, post-production, multi-user, generic orchestration, or distributed infrastructure scope.

## 8. Completion handoff

After each milestone, produce:

```text
changed files
schema changes
API routes
frontend screens
focused test results
full regression result
known limitations
next milestone readiness
```

Do not declare the whole MVP complete before Milestone 4 passes.
