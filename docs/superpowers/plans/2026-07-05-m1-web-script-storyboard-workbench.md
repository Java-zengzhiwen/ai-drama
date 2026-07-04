# Milestone 1 — Web Script and Storyboard Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a local user create a project and chapter, enter source/context, generate/edit/validate/approve a script, then generate/edit/validate/approve a Canonical Storyboard from the Web UI.

**Architecture:** Add a FastAPI application package around the existing runtime and a React/TypeScript client. Product metadata is stored in new tables on the existing SQLite connection; immutable script/storyboard revisions remain in `RuntimeStore`. Add direct-input runtime execution so Web workflows do not depend on acceptance fixture directories.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, existing runtime, SQLite, React, TypeScript, Vite, TanStack Query, React Router, Vitest.

---

### Task 1: Install the approved MVP governance baseline

**Files:**
- Create: `docs/superpowers/specs/2026-07-05-ai-drama-web-production-mvp-design-v2.md`
- Create: `docs/superpowers/plans/2026-07-05-ai-drama-web-production-mvp-implementation.md`
- Create: `docs/superpowers/plans/2026-07-05-m1-web-script-storyboard-workbench.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Copy the approved design and plans into the repository**

Copy the approved documents without changing their requirements.

- [ ] **Step 2: Replace the historical Phase 3 execution section in `AGENTS.md`**

```markdown
## AI Drama Web Production MVP

Before MVP planning, implementation, testing, review, commit, or push, read:

- `docs/superpowers/specs/2026-07-05-ai-drama-web-production-mvp-design-v2.md`
- `docs/superpowers/plans/2026-07-05-ai-drama-web-production-mvp-implementation.md`
- the current approved milestone plan

Rules:

- The Web Production MVP design is the current product scope authority.
- Historical Phase 3B–3E plans are paused and must not control new implementation.
- Preserve existing Script, Storyboard, Bundle, Store, and Phase 3A behavior.
- Execute milestones in order and do not enter a later milestone before the current gate passes.
- Do not add LibTV execution, post-production, multi-user, generic workflow, or distributed infrastructure scope.
- Use TDD and keep every milestone independently usable.
- Do not weaken existing tests, schemas, fixtures, or acceptance checks.
```

- [ ] **Step 3: Verify governance replacement**

```bash
python3 - <<'PY'
from pathlib import Path
text = Path('AGENTS.md').read_text(encoding='utf-8')
assert '3A Store/Migration -> 3B Canonical/Validators' not in text
assert 'AI Drama Web Production MVP' in text
print('PASS')
PY
```

Expected: `PASS`.

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md docs/superpowers/specs docs/superpowers/plans
git commit -m "docs: establish web production mvp program"
```

### Task 2: Add Web dependencies and package skeleton

**Files:**
- Modify: `pyproject.toml`
- Create: `ai_drama_web/__init__.py`
- Create: `ai_drama_web/config.py`
- Create: `ai_drama_web/app.py`
- Create: `tests/web/test_app_health.py`

- [ ] **Step 1: Write the failing health test**

```python
from fastapi.testclient import TestClient
from ai_drama_web.app import create_app


def test_health_returns_ok(tmp_path):
    app = create_app(data_root=tmp_path / "runtime-data", skills_root="skills")
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Verify failure**

```bash
python3 -m pytest tests/web/test_app_health.py -q
```

Expected: FAIL because `ai_drama_web` or FastAPI is unavailable.

- [ ] **Step 3: Update `pyproject.toml`**

```toml
requires-python = ">=3.11"

dependencies = [
  "PyYAML>=6.0",
  "openai>=1.0",
  "fastapi>=0.115,<1",
  "uvicorn[standard]>=0.30,<1",
  "pydantic-settings>=2.6,<3",
  "python-multipart>=0.0.12,<1",
  "httpx>=0.27,<1",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "pytest-asyncio>=0.24,<1",
  "respx>=0.21,<1",
]

[project.scripts]
ai-drama = "ai_drama_runtime.cli:main"
ai-drama-web = "ai_drama_web.app:main"

[tool.setuptools.packages.find]
include = ["ai_drama_runtime*", "ai_drama_web*"]
```

- [ ] **Step 4: Implement configuration**

```python
# ai_drama_web/config.py
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    data_root: Path = Path("runtime-data")
    skills_root: Path = Path("skills")
    runtime_provider: str = "mock"
    runtime_model: str = ""
    model_config = SettingsConfigDict(env_prefix="AI_DRAMA_", extra="ignore")
```

- [ ] **Step 5: Implement application factory**

```python
# ai_drama_web/app.py
from pathlib import Path
from fastapi import FastAPI
from .config import Settings


def create_app(*, data_root: Path | None = None, skills_root: str | Path | None = None) -> FastAPI:
    settings = Settings()
    if data_root is not None:
        settings.data_root = Path(data_root)
    if skills_root is not None:
        settings.skills_root = Path(skills_root)
    app = FastAPI(title="AI Drama Web Production MVP")
    app.state.settings = settings

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def main() -> None:
    import uvicorn
    uvicorn.run("ai_drama_web.app:create_app", factory=True, host="127.0.0.1", port=8000)
```

- [ ] **Step 6: Install and test**

```bash
pip install -e ".[dev]"
python3 -m pytest tests/web/test_app_health.py -q
```

Expected: `1 passed`.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml ai_drama_web tests/web/test_app_health.py
git commit -m "feat: add fastapi application skeleton"
```

### Task 3: Add product metadata persistence

**Files:**
- Create: `ai_drama_web/store.py`
- Create: `ai_drama_web/models.py`
- Create: `tests/web/test_product_store.py`

- [ ] **Step 1: Write failing persistence test**

```python
from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.store import ProductStore


def test_project_chapter_and_source_revision_are_persisted(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)
    project = store.create_project(
        name="生死",
        description="古装重生短剧",
        series_canon="明代商贾世界",
        characters_context="沈清荷、沈清莲",
        production_brief="真人写实，16:9，低饱和",
    )
    chapter = store.create_chapter(project.project_id, "第一章", 1)
    source = store.create_source_revision(chapter.chapter_id, "第一章正文")
    assert store.get_project(project.project_id).name == "生死"
    assert store.get_chapter(chapter.chapter_id).current_source_revision_id == source.source_revision_id
    assert runtime.read_text(source.object_id) == "第一章正文"
```

- [ ] **Step 2: Verify failure**

```bash
python3 -m pytest tests/web/test_product_store.py -q
```

Expected: FAIL because `ProductStore` does not exist.

- [ ] **Step 3: Implement immutable records**

```python
# ai_drama_web/models.py
from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectRecord:
    project_id: str
    name: str
    description: str
    series_canon: str
    characters_context: str
    production_brief: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ChapterRecord:
    chapter_id: str
    project_id: str
    title: str
    position: int
    current_source_revision_id: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ChapterSourceRevisionRecord:
    source_revision_id: str
    chapter_id: str
    number: int
    object_id: str
    content_hash: str
    created_at: str
```

- [ ] **Step 4: Implement schema**

```sql
CREATE TABLE IF NOT EXISTS projects (
  project_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT NOT NULL,
  series_canon TEXT NOT NULL,
  characters_context TEXT NOT NULL,
  production_brief TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chapters (
  chapter_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE RESTRICT,
  title TEXT NOT NULL,
  position INTEGER NOT NULL,
  current_source_revision_id TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(project_id, position)
);
CREATE TABLE IF NOT EXISTS chapter_source_revisions (
  source_revision_id TEXT PRIMARY KEY,
  chapter_id TEXT NOT NULL REFERENCES chapters(chapter_id) ON DELETE RESTRICT,
  number INTEGER NOT NULL,
  object_id TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(chapter_id, number)
);
```

Use `uuid.uuid4().hex`, `now_iso()`, and `RuntimeStore.write_text_object()`; update `chapters.current_source_revision_id` in the same transaction as source insertion.

- [ ] **Step 5: Run tests and regressions**

```bash
python3 -m pytest tests/web/test_product_store.py -q
python3 -m pytest -q tests/test_shot_prompt_store_migration.py tests/test_storyboard_legacy_migration.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add ai_drama_web/models.py ai_drama_web/store.py tests/web/test_product_store.py
git commit -m "feat: add project chapter and source persistence"
```

### Task 4: Add project/chapter API

**Files:**
- Create: `ai_drama_web/dependencies.py`
- Create: `ai_drama_web/schemas/projects.py`
- Create: `ai_drama_web/services/projects.py`
- Create: `ai_drama_web/routers/projects.py`
- Modify: `ai_drama_web/app.py`
- Create: `tests/web/conftest.py`
- Create: `tests/web/test_projects_api.py`

- [ ] **Step 1: Write failing API test**

```python
def test_create_project_chapter_and_source(client):
    project = client.post("/api/projects", json={
        "name": "生死",
        "description": "古装重生短剧",
        "series_canon": "明代商贾世界",
        "characters_context": "沈清荷、沈清莲",
        "production_brief": "真人写实，16:9",
    }).json()
    chapter = client.post(f"/api/projects/{project['project_id']}/chapters", json={
        "title": "第一章",
        "position": 1,
    }).json()
    source = client.post(f"/api/chapters/{chapter['chapter_id']}/source-revisions", json={
        "content": "第一章正文",
    }).json()
    assert source["chapter_id"] == chapter["chapter_id"]
    assert client.get(f"/api/chapters/{chapter['chapter_id']}").json()["source_text"] == "第一章正文"
```

- [ ] **Step 2: Verify 404 failure**

```bash
python3 -m pytest tests/web/test_projects_api.py -q
```

- [ ] **Step 3: Implement schemas and dependencies**

```python
# ai_drama_web/dependencies.py
from fastapi import Request
from ai_drama_runtime.store import RuntimeStore
from .store import ProductStore


def get_runtime_store(request: Request) -> RuntimeStore:
    return request.app.state.runtime_store


def get_product_store(request: Request) -> ProductStore:
    return request.app.state.product_store
```

Define `ProjectCreate`, `ProjectRead`, `ChapterCreate`, `ChapterRead`, `SourceRevisionCreate`, and `SourceRevisionRead`; reject blank names/content and require position `>= 1`.

- [ ] **Step 4: Implement routes**

```text
POST /api/projects
GET  /api/projects
GET  /api/projects/{project_id}
POST /api/projects/{project_id}/chapters
GET  /api/chapters/{chapter_id}
POST /api/chapters/{chapter_id}/source-revisions
```

Return 404 for missing records and 409 for duplicate chapter position.

- [ ] **Step 5: Run tests and commit**

```bash
python3 -m pytest tests/web/test_projects_api.py -q
git add ai_drama_web tests/web
git commit -m "feat: add project and chapter web api"
```

### Task 5: Add direct-input script execution

**Files:**
- Modify: `ai_drama_runtime/request.py`
- Modify: `ai_drama_runtime/services.py`
- Create: `tests/test_web_script_runtime.py`

- [ ] **Step 1: Write failing builder test**

```python
from ai_drama_runtime.request import build_runtime_request_from_inputs


def test_direct_input_request_is_canonical(skill_package):
    request = build_runtime_request_from_inputs(
        skill_package,
        inputs={
            "source_chapter": "正文",
            "series_canon": "世界观",
            "characters": "人物",
            "production_brief": "制作要求",
        },
        provider="mock",
        model="mock-script-v1",
    )
    assert [item["logical_type"] for item in request.payload["inputs"]] == [
        "characters", "production_brief", "series_canon", "source_chapter"
    ]
```

- [ ] **Step 2: Verify failure**

```bash
python3 -m pytest tests/test_web_script_runtime.py -q
```

- [ ] **Step 3: Implement direct-input builder**

```python
def build_runtime_request_from_inputs(skill, inputs, provider, model, timeout_seconds=60):
    instruction_text = skill.instructions_entry.read_text(encoding="utf-8")
    profile = (skill.metadata.get("execution_profiles") or [{}])[0]
    context_files = _unique_file_items(skill.root, skill.context_files + skill.schemas + skill.contracts)
    normalized_inputs = [
        {
            "logical_type": logical_type,
            "relative_path": "web-inputs/%s.md" % logical_type,
            "sha256": _sha(content),
            "content": content,
        }
        for logical_type, content in sorted(inputs.items())
    ]
    return RuntimeRequest({
        "request_format_version": REQUEST_FORMAT_VERSION,
        "skill": {
            "skill_id": skill.skill_id,
            "version": skill.version,
            "package_hash": skill.content_hash,
            "execution_profile": profile.get("profile_id", "markdown-script-mvp-v1"),
        },
        "system_instruction": SYSTEM_INSTRUCTION,
        "skill_instruction": {
            "relative_path": skill.instructions_entry.relative_to(skill.root).as_posix(),
            "sha256": _sha(instruction_text),
            "content": instruction_text,
        },
        "context_files": context_files,
        "inputs": normalized_inputs,
        "output_contract": {
            "profile": profile.get("profile_id", "markdown-script-mvp-v1"),
            "format": profile.get("output_format", "markdown"),
            "parser_version": PARSER_VERSION,
            "supported_artifacts": profile.get("supported_artifacts", ["creator_facing_markdown_script"]),
            "unsupported_bundle_artifacts": profile.get("unsupported_bundle_artifacts", []),
        },
        "runtime_config": {"provider": provider, "model": model or "", "timeout_seconds": timeout_seconds},
    })
```

- [ ] **Step 4: Add `RuntimeService.run_script_inputs()`**

Refactor shared response parsing/persistence from `run_acceptance()` into `_execute_script_request()`, then call it from both existing acceptance execution and new direct-input execution. Persist all four input snapshots.

- [ ] **Step 5: Run tests and commit**

```bash
python3 -m pytest tests/test_web_script_runtime.py -q
python3 -m pytest -q
git add ai_drama_runtime/request.py ai_drama_runtime/services.py tests/test_web_script_runtime.py
git commit -m "feat: run script skill from web inputs"
```

### Task 6: Add immutable manual revision editing

**Files:**
- Modify: `ai_drama_runtime/services.py`
- Modify: `ai_drama_runtime/store.py`
- Create: `tests/test_manual_revision.py`

- [ ] **Step 1: Write failing test**

```python
def test_manual_revision_supersedes_generated_revision(runtime_service, generated_script_revision):
    edited = runtime_service.create_manual_revision(
        source_revision_id=generated_script_revision.revision_id,
        content="# 第一场\n修改后的剧本",
        actor="local-user",
    )
    assert edited.derivation_type == "manual_edit"
    assert edited.supersedes_revision_id == generated_script_revision.revision_id
    assert edited.number == generated_script_revision.number + 1
    assert edited.approval_status == "pending"
```

- [ ] **Step 2: Implement synthetic manual-edit run**

Create a `runs` row using:

```text
skill_id = manual-editor
skill_version = 1
runtime = manual
provider = local-user
model = manual-edit
status = SUCCEEDED
```

Insert a new revision with the original artifact/project/chapter/profile/parser fields, `derivation_type="manual_edit"`, and `supersedes_revision_id=source_revision_id`. Validate Canonical Storyboard JSON before insertion and use `canonical_storyboard_hash()`.

- [ ] **Step 3: Run tests and commit**

```bash
python3 -m pytest tests/test_manual_revision.py -q
python3 -m pytest -q
git add ai_drama_runtime/services.py ai_drama_runtime/store.py tests/test_manual_revision.py
git commit -m "feat: add immutable manual revisions"
```

### Task 7: Add Script workflow API

**Files:**
- Create: `ai_drama_web/schemas/workflows.py`
- Create: `ai_drama_web/services/script_workflow.py`
- Create: `ai_drama_web/routers/scripts.py`
- Modify: `ai_drama_web/app.py`
- Create: `tests/web/test_script_workflow_api.py`

- [ ] **Step 1: Write failing end-to-end API test**

Exercise:

```text
POST /api/chapters/{id}/script/generate
GET  /api/chapters/{id}/script/revisions
PUT  /api/script-revisions/{revision_id}
POST /api/script-revisions/{revision_id}/approve
```

Assert edited revision pending and approved revision current.

- [ ] **Step 2: Implement service**

Resolve `ai-drama-script-adaptation-skill@v0.6.1-rc2.4`, call `run_script_inputs()`, expose content and validation, use `create_manual_revision()`, `approve_revision()`, and `reject_revision()`. Use artifact ID `f"{chapter_id}:script"`.

- [ ] **Step 3: Implement error mapping**

Map `WorkflowGateError` to 409 and `ApprovalBlocked` to 422 with a stable `{error_code,error_message}` body.

- [ ] **Step 4: Run tests and commit**

```bash
python3 -m pytest tests/web/test_script_workflow_api.py -q
git add ai_drama_web tests/web/test_script_workflow_api.py
git commit -m "feat: expose script workflow api"
```

### Task 8: Add Storyboard workflow API

**Files:**
- Create: `ai_drama_web/services/storyboard_workflow.py`
- Create: `ai_drama_web/routers/storyboards.py`
- Modify: `ai_drama_web/app.py`
- Create: `tests/web/test_storyboard_workflow_api.py`

- [ ] **Step 1: Write failing gate and happy-path tests**

Verify unapproved script returns 409 `SOURCE_REVISION_NOT_APPROVED`; approve script and verify Canonical Storyboard generation.

- [ ] **Step 2: Implement service and routes**

Resolve the active Canonical Storyboard package, call existing `run_storyboard()`, allow immutable manual edits, and approve/reject with existing runtime methods.

```text
POST /api/chapters/{chapter_id}/storyboard/generate
GET  /api/chapters/{chapter_id}/storyboard/revisions
PUT  /api/storyboard-revisions/{revision_id}
POST /api/storyboard-revisions/{revision_id}/approve
POST /api/storyboard-revisions/{revision_id}/reject
```

- [ ] **Step 3: Run tests and commit**

```bash
python3 -m pytest tests/web/test_storyboard_workflow_api.py -q
python3 -m pytest -q
git add ai_drama_web tests/web/test_storyboard_workflow_api.py
git commit -m "feat: expose storyboard workflow api"
```

### Task 9: Add derived chapter status

**Files:**
- Create: `ai_drama_web/services/chapter_status.py`
- Modify: `ai_drama_web/routers/projects.py`
- Create: `tests/web/test_chapter_status.py`

- [ ] **Step 1: Write table-driven tests**

Cover `source_ready`, `script_draft`, `script_approved`, `storyboard_draft`, and `storyboard_approved`. Status is derived, never manually writable.

- [ ] **Step 2: Implement result**

```python
{
    "status": "storyboard_approved",
    "blocking_reason": "",
    "next_action": "open_assets",
}
```

- [ ] **Step 3: Run tests and commit**

```bash
python3 -m pytest tests/web/test_chapter_status.py -q
git add ai_drama_web tests/web/test_chapter_status.py
git commit -m "feat: derive chapter workflow status"
```

### Task 10: Scaffold React client

**Files:**
- Create: `web/package.json`
- Create: `web/tsconfig.json`
- Create: `web/vite.config.ts`
- Create: `web/index.html`
- Create: `web/src/main.tsx`
- Create: `web/src/app/App.tsx`
- Create: `web/src/api/client.ts`
- Create: `web/src/test/setup.ts`
- Create: `web/src/app/App.test.tsx`

- [ ] **Step 1: Create `package.json`**

```json
{
  "name": "ai-drama-web",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "test": "vitest",
    "test:e2e": "playwright test"
  },
  "dependencies": {
    "@tanstack/react-query": "^5.62.0",
    "antd": "^5.22.0",
    "axios": "^1.7.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^7.1.0"
  },
  "devDependencies": {
    "@playwright/test": "^1.49.0",
    "@testing-library/jest-dom": "^6.6.0",
    "@testing-library/react": "^16.1.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "jsdom": "^25.0.0",
    "typescript": "^5.7.0",
    "vite": "^6.0.0",
    "vitest": "^2.1.0"
  }
}
```

- [ ] **Step 2: Write route smoke test**

Assert `/projects` renders `项目` and unknown routes redirect to `/projects`.

- [ ] **Step 3: Implement app shell**

Use `BrowserRouter`, `QueryClientProvider`, Ant Design layout, and routes for project list, dashboard, and chapter workspace.

- [ ] **Step 4: Install, test, build, commit**

```bash
npm --prefix web install
npm --prefix web run test -- --run
npm --prefix web run build
git add web
git commit -m "feat: scaffold react web client"
```

### Task 11: Implement project list and dashboard

**Files:**
- Create: `web/src/features/projects/api.ts`
- Create: `web/src/features/projects/ProjectListPage.tsx`
- Create: `web/src/features/projects/ProjectDashboardPage.tsx`
- Create: `web/src/features/projects/ProjectPages.test.tsx`
- Modify: `web/src/app/App.tsx`

- [ ] **Step 1: Write failing UI tests**

Test project creation, chapter creation, and chapter status/next action.

- [ ] **Step 2: Implement typed API**

```typescript
export type ProjectCreate = {
  name: string;
  description: string;
  series_canon: string;
  characters_context: string;
  production_brief: string;
};
```

- [ ] **Step 3: Implement pages and run tests**

```bash
npm --prefix web run test -- --run
git add web/src
git commit -m "feat: add project and chapter web screens"
```

### Task 12: Implement Source and Script tabs

**Files:**
- Create: `web/src/features/chapter/ChapterWorkspace.tsx`
- Create: `web/src/features/chapter/SourceTab.tsx`
- Create: `web/src/features/script/ScriptTab.tsx`
- Create: `web/src/features/script/api.ts`
- Create: `web/src/features/script/ScriptTab.test.tsx`
- Modify: `web/src/app/App.tsx`

- [ ] **Step 1: Write failing tests**

Test source save, script generation, edit-as-new-revision, QC display, and approval.

- [ ] **Step 2: Implement workspace tabs**

```text
原文
剧本
分镜
资料与资产
Shot Prompt
Agnes 生成
结果与重跑
```

Disable later tabs and show blocking reason.

- [ ] **Step 3: Implement UI and commit**

```bash
npm --prefix web run test -- --run
git add web/src
git commit -m "feat: add source and script workspace tabs"
```

### Task 13: Implement Storyboard tab

**Files:**
- Create: `web/src/features/storyboard/api.ts`
- Create: `web/src/features/storyboard/StoryboardTab.tsx`
- Create: `web/src/features/storyboard/ShotEditor.tsx`
- Create: `web/src/features/storyboard/StoryboardTab.test.tsx`
- Modify: `web/src/features/chapter/ChapterWorkspace.tsx`

- [ ] **Step 1: Write failing tests**

Verify script gate, generation, canonical shot editing, save-as-new-revision, and approval.

- [ ] **Step 2: Preserve canonical field names**

```text
shot_order
duration_seconds
shot_size
camera_angle
camera_movement
visual_composition
character_positions
character_actions
emotion_performance
dialogue
continuity_in
continuity_out
```

- [ ] **Step 3: Run tests and commit**

```bash
npm --prefix web run test -- --run
python3 -m pytest tests/web/test_storyboard_workflow_api.py -q
git add web/src
git commit -m "feat: add canonical storyboard web editor"
```

### Task 14: Add Milestone 1 verification

**Files:**
- Create: `web/playwright.config.ts`
- Create: `web/tests/m1-workflow.spec.ts`
- Create: `tools/verify_m1_web_workflow.py`
- Modify: `README.md`

- [ ] **Step 1: Add Playwright flow**

Create project/chapter, save source, generate/approve script, generate/approve storyboard, and assert `storyboard_approved`.

- [ ] **Step 2: Add backend verifier**

Print exactly `M1_WEB_WORKFLOW_PASS`.

- [ ] **Step 3: Run gate and commit**

```bash
python3 tools/verify_m1_web_workflow.py
python3 migration/tools/verify_migration.py
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q
npm --prefix web run test -- --run
npm --prefix web run build
git add web tools/verify_m1_web_workflow.py README.md
git commit -m "test: verify web script storyboard milestone"
```
