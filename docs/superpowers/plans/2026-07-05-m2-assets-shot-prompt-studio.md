# Milestone 2 — Profiles, Assets, and Shot Prompt Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the user maintain minimal production profiles, upload or generate image assets, analyze per-shot asset requirements, and generate/edit/version ready Shot Prompts from an approved Canonical Storyboard.

**Architecture:** Extend the product store with profile, asset, binding, and requirement tables. Add a minimal Agnes image client behind the thin backend interface. Add a new Shot Prompt canonical module and focused Skill package; persist prompt revisions through the existing Artifact/Revision infrastructure and the Phase 3A shot-prompt artifact business key.

**Tech Stack:** Existing Milestone 1 stack, JSON canonicalization, HTTPX/RESpx, multipart upload, Agnes Image API, React asset/prompt screens.

---

### Task 1: Add production profile persistence and API

**Files:**
- Modify: `ai_drama_web/models.py`
- Modify: `ai_drama_web/store.py`
- Create: `ai_drama_web/schemas/profiles.py`
- Create: `ai_drama_web/services/profiles.py`
- Create: `ai_drama_web/routers/profiles.py`
- Modify: `ai_drama_web/app.py`
- Create: `tests/web/test_profiles_api.py`

- [ ] **Step 1: Write failing CRUD tests**

Create character, scene, prop, and style profiles; update one; list by chapter and type.

- [ ] **Step 2: Add schema**

```sql
CREATE TABLE IF NOT EXISTS production_profiles (
  profile_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE RESTRICT,
  chapter_id TEXT NOT NULL DEFAULT '',
  profile_type TEXT NOT NULL CHECK (profile_type IN ('character','scene','prop','style')),
  name TEXT NOT NULL,
  payload_object_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS production_profiles_scope_idx
  ON production_profiles(project_id, chapter_id, profile_type, name);
```

Store normalized JSON payloads in object storage. Define exact Pydantic payloads from the approved design and reject extra fields.

- [ ] **Step 3: Add routes and verify**

```text
POST /api/projects/{project_id}/profiles
GET  /api/projects/{project_id}/profiles
PUT  /api/profiles/{profile_id}
```

```bash
python3 -m pytest tests/web/test_profiles_api.py -q
git add ai_drama_web tests/web/test_profiles_api.py
git commit -m "feat: add production profiles"
```

### Task 2: Add asset storage, bindings, and upload API

**Files:**
- Modify: `ai_drama_web/models.py`
- Modify: `ai_drama_web/store.py`
- Create: `ai_drama_web/schemas/assets.py`
- Create: `ai_drama_web/services/assets.py`
- Create: `ai_drama_web/routers/assets.py`
- Modify: `ai_drama_web/app.py`
- Create: `tests/web/test_assets_api.py`

- [ ] **Step 1: Write failing upload/binding/state tests**

Upload PNG, bind to character, mark usable, and verify exact object hash.

- [ ] **Step 2: Add tables**

```sql
CREATE TABLE IF NOT EXISTS assets (
  asset_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE RESTRICT,
  chapter_id TEXT NOT NULL DEFAULT '',
  asset_type TEXT NOT NULL CHECK (asset_type IN ('character_reference','character_outfit','scene_reference','scene_angle','prop_reference','shot_keyframe')),
  name TEXT NOT NULL,
  object_id TEXT NOT NULL,
  media_type TEXT NOT NULL,
  width INTEGER NOT NULL DEFAULT 0,
  height INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL CHECK (status IN ('draft','generating','usable','rejected','failed')),
  source_type TEXT NOT NULL CHECK (source_type IN ('upload','agnes','derived')),
  source_job_id TEXT NOT NULL DEFAULT '',
  metadata_object_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS asset_bindings (
  binding_id TEXT PRIMARY KEY,
  asset_id TEXT NOT NULL REFERENCES assets(asset_id) ON DELETE RESTRICT,
  target_type TEXT NOT NULL CHECK (target_type IN ('character','scene','prop','shot')),
  target_id TEXT NOT NULL,
  role TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(asset_id, target_type, target_id, role)
);
```

Accept only PNG/JPEG/WebP and enforce configured size limit.

- [ ] **Step 3: Add routes and verify**

```text
POST /api/chapters/{chapter_id}/assets
GET  /api/chapters/{chapter_id}/assets
POST /api/assets/{asset_id}/bindings
POST /api/assets/{asset_id}/mark-usable
POST /api/assets/{asset_id}/reject
GET  /api/assets/{asset_id}/content
```

```bash
python3 -m pytest tests/web/test_assets_api.py -q
git add ai_drama_web tests/web/test_assets_api.py
git commit -m "feat: add asset upload and bindings"
```

### Task 3: Add generation backend contracts

**Files:**
- Create: `ai_drama_web/providers/base.py`
- Create: `ai_drama_web/providers/models.py`
- Create: `ai_drama_web/providers/fake.py`
- Create: `tests/providers/test_fake_generation_backend.py`

- [ ] **Step 1: Write failing fake backend tests**

Verify image create/status/result and unsupported video behavior.

- [ ] **Step 2: Implement contracts**

```python
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ImageGenerationRequest:
    prompt: str
    size: str
    input_images: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VideoGenerationRequest:
    prompt: str
    duration_seconds: int
    input_images: list[str] = field(default_factory=list)
    negative_prompt: str = ""
    parameters: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderJob:
    provider_job_id: str
    status: str
    raw: dict


@dataclass(frozen=True)
class ProviderResult:
    provider_job_id: str
    media_type: str
    url: str
    content: bytes | None
    raw: dict


class GenerationBackend(Protocol):
    def create_image_job(self, request: ImageGenerationRequest) -> ProviderJob: ...
    def create_video_job(self, request: VideoGenerationRequest) -> ProviderJob: ...
    def get_job_status(self, provider_job_id: str) -> ProviderJob: ...
    def fetch_result(self, provider_job_id: str) -> ProviderResult: ...
```

- [ ] **Step 3: Verify and commit**

```bash
python3 -m pytest tests/providers/test_fake_generation_backend.py -q
git add ai_drama_web/providers tests/providers
git commit -m "feat: add generation backend contracts"
```

### Task 4: Add Agnes local secret settings

**Files:**
- Create: `ai_drama_web/secrets.py`
- Create: `ai_drama_web/schemas/settings.py`
- Create: `ai_drama_web/routers/settings.py`
- Modify: `ai_drama_web/app.py`
- Create: `tests/web/test_agnes_settings_api.py`
- Create: `web/src/features/settings/AgnesSettingsPage.tsx`
- Create: `web/src/features/settings/AgnesSettingsPage.test.tsx`
- Modify: `web/src/app/App.tsx`

- [ ] **Step 1: Write failing secret-safety tests**

Verify setting a key, reading only `{configured, masked_suffix}`, deleting the key, file mode `0600`, and absence of the full key in API responses and logs.

- [ ] **Step 2: Implement `LocalSecretStore`**

Store the Agnes key at `runtime-data/secrets/agnes-api-key` using an atomic temporary file, `os.replace()`, and mode `0o600`. Expose only:

```python
class LocalSecretStore:
    def set_agnes_api_key(self, value: str) -> None: ...
    def get_agnes_api_key(self) -> str: ...
    def delete_agnes_api_key(self) -> None: ...
    def agnes_status(self) -> dict[str, object]: ...
```

`agnes_status()` returns `{"configured": True, "masked_suffix": "1234"}` and never returns the key.

- [ ] **Step 3: Add settings API**

```text
GET    /api/settings/agnes
PUT    /api/settings/agnes
DELETE /api/settings/agnes
```

The PUT body is `{"api_key":"..."}`. Require a nonblank value and never echo it.

- [ ] **Step 4: Add settings page**

Route `/settings/agnes` shows configured state, a password input to replace the key, and a remove action. Do not persist the key in localStorage or query cache.

- [ ] **Step 5: Verify and commit**

```bash
python3 -m pytest tests/web/test_agnes_settings_api.py -q
npm --prefix web run test -- --run
git add ai_drama_web web/src tests/web/test_agnes_settings_api.py
git commit -m "feat: add secure local agnes settings"
```

### Task 5: Implement Agnes image generation

**Files:**
- Create: `ai_drama_web/providers/agnes.py`
- Create: `ai_drama_web/providers/errors.py`
- Modify: `ai_drama_web/config.py`
- Create: `tests/providers/test_agnes_image_backend.py`

- [ ] **Step 1: Write mocked HTTP tests**

Verify endpoint, `agnes-image-2.1-flash`, no image field for text-to-image, `extra_body.image` for image-to-image, and secret only in Authorization header.

- [ ] **Step 2: Implement error mapping**

```text
authentication
rate_limited
invalid_request
provider_busy
timeout
unknown_provider_error
```

- [ ] **Step 3: Implement request**

```python
payload = {
    "model": "agnes-image-2.1-flash",
    "prompt": request.prompt,
    "size": request.size,
    "extra_body": {"response_format": "url"},
}
if request.input_images:
    payload["extra_body"]["image"] = request.input_images
```

Treat `data[0].url` as completed image result.

- [ ] **Step 4: Verify and commit**

```bash
python3 -m pytest tests/providers/test_agnes_image_backend.py -q
git add ai_drama_web/providers ai_drama_web/config.py tests/providers/test_agnes_image_backend.py
git commit -m "feat: integrate agnes image generation"
```

### Task 6: Add asset image generation service and API

**Files:**
- Create: `ai_drama_web/services/asset_generation.py`
- Modify: `ai_drama_web/routers/assets.py`
- Create: `tests/web/test_asset_generation_api.py`

- [ ] **Step 1: Write failing fake-provider API test**

Submit text-to-image, persist result as `source_type='agnes'`, and leave status draft until user marks usable.

- [ ] **Step 2: Implement Data URI helper**

```python
import base64


def asset_data_uri(media_type: str, data: bytes) -> str:
    return f"data:{media_type};base64,{base64.b64encode(data).decode('ascii')}"
```

- [ ] **Step 3: Add route and verify**

```text
POST /api/chapters/{chapter_id}/assets/generate-image
```

```bash
python3 -m pytest tests/web/test_asset_generation_api.py -q
git add ai_drama_web tests/web/test_asset_generation_api.py
git commit -m "feat: generate chapter assets with agnes"
```

### Task 7: Add asset requirement analysis

**Files:**
- Create: `ai_drama_web/services/asset_requirements.py`
- Modify: `ai_drama_web/store.py`
- Create: `ai_drama_web/routers/asset_requirements.py`
- Modify: `ai_drama_web/app.py`
- Create: `tests/web/test_asset_requirements.py`

- [ ] **Step 1: Write failing canonical analysis test**

Use two characters, one scene, one prop, and only one usable character asset.

- [ ] **Step 2: Add immutable requirement set**

```sql
CREATE TABLE IF NOT EXISTS asset_requirement_sets (
  requirement_set_id TEXT PRIMARY KEY,
  chapter_id TEXT NOT NULL REFERENCES chapters(chapter_id) ON DELETE RESTRICT,
  storyboard_revision_id TEXT NOT NULL,
  content_object_id TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  created_at TEXT NOT NULL
);
```

- [ ] **Step 3: Implement analyzer**

Read current canonical scene/shot character fields and match profile IDs plus usable bindings. Output statuses `ready`, `missing_assets`, `asset_generation_in_progress`, or `asset_review_required`.

- [ ] **Step 4: Add routes, verify, commit**

```text
POST /api/chapters/{chapter_id}/asset-requirements/analyze
GET  /api/chapters/{chapter_id}/asset-requirements/latest
```

```bash
python3 -m pytest tests/web/test_asset_requirements.py -q
git add ai_drama_web tests/web/test_asset_requirements.py
git commit -m "feat: analyze storyboard asset requirements"
```

### Task 8: Add Shot Prompt canonical model

**Files:**
- Create: `ai_drama_runtime/shot_prompt_canonical.py`
- Modify: `ai_drama_runtime/parser.py`
- Create: `tests/test_shot_prompt_canonical.py`

- [ ] **Step 1: Write failing canonical tests**

Test deterministic serialization, duplicate IDs, invalid duration, missing prompt, missing asset refs, and stable hash.

- [ ] **Step 2: Implement exact contract**

Top-level keys: `schema_version`, `project_id`, `chapter_id`, `source_storyboard_revision_id`, `shots`.

Shot keys: `shot_id`, `shot_order`, `duration_seconds`, `scene_id`, `character_ids`, `prop_ids`, `asset_refs`, `camera`, `action`, `emotion`, `dialogue`, `positive_prompt`, `negative_prompt`, `continuity_notes`, `agnes_video_params`.

Use `shot-prompt-canonical-v1`, NFC normalization, canonical JSON, no extra fields, 5–15 seconds, and unique IDs.

- [ ] **Step 3: Add parser and verify**

```python
SHOT_PROMPT_CANONICAL_PARSER_VERSION = "shot-prompt-canonical-json-v1"
```

Accept direct JSON and OpenAI-compatible `choices[0].message.content`.

```bash
python3 -m pytest tests/test_shot_prompt_canonical.py -q
git add ai_drama_runtime tests/test_shot_prompt_canonical.py
git commit -m "feat: add shot prompt canonical format"
```

### Task 9: Create Shot Prompt Skill package

**Files:**
- Create: `skills/ai-drama-shot-prompt-skill/v0.1.0/skill.json`
- Create: `skills/ai-drama-shot-prompt-skill/v0.1.0/SKILL.md`
- Create: `skills/ai-drama-shot-prompt-skill/v0.1.0/README.md`
- Create: `skills/ai-drama-shot-prompt-skill/v0.1.0/schemas/shot-prompt-set.schema.json`
- Create: `skills/ai-drama-shot-prompt-skill/v0.1.0/contracts/shot-prompt-contract-v1.md`
- Create: `skills/ai-drama-shot-prompt-skill/v0.1.0/validators/validate_shot_prompt_set.py`
- Create: `tests/test_shot_prompt_skill_package.py`

- [ ] **Step 1: Write failing package test**

Resolve `ai-drama-shot-prompt-skill@v0.1.0` and require one structure validator.

- [ ] **Step 2: Create package metadata**

Use profile `shot-prompt-canonical-v1`, output `shot_prompt_set`, parser `shot-prompt-canonical-json-v1`, and unsupported outputs `libtv_execution_package` and `post_production_package`.

- [ ] **Step 3: Write Skill constraints and validator**

Require one-to-one shot mapping, ID/duration/dialogue/continuity preservation, explicit consistency rules, positive/negative prompts, and valid asset refs. Validator imports `shot_prompt_canonical.py`, writes JSON report, and exits nonzero on error.

- [ ] **Step 4: Verify and commit**

```bash
python3 -m pytest tests/test_shot_prompt_skill_package.py -q
git add skills/ai-drama-shot-prompt-skill tests/test_shot_prompt_skill_package.py
git commit -m "feat: add focused shot prompt skill"
```

### Task 10: Add Shot Prompt runtime execution

**Files:**
- Modify: `ai_drama_runtime/request.py`
- Modify: `ai_drama_runtime/services.py`
- Create: `tests/test_shot_prompt_runtime.py`

- [ ] **Step 1: Write gate and persistence tests**

Cover missing/unapproved/stale storyboard, successful mock generation, dependency, and Phase 3A business-key reuse.

- [ ] **Step 2: Implement request inputs**

```text
source_storyboard_revision_id
source_storyboard_content_hash
storyboard_canonical
production_profiles
asset_requirements
asset_bindings
```

- [ ] **Step 3: Implement `run_shot_prompt()`**

Require current approved fresh Canonical Storyboard, call `ensure_shot_prompt_artifact()`, parse canonical response, insert `shot_prompt_set` revision/profile, create storyboard dependency, and run validator.

- [ ] **Step 4: Verify and commit**

```bash
python3 -m pytest tests/test_shot_prompt_runtime.py -q
python3 -m pytest -q
git add ai_drama_runtime tests/test_shot_prompt_runtime.py
git commit -m "feat: run and persist shot prompt revisions"
```

### Task 11: Add Shot Prompt Service and API

**Files:**
- Create: `ai_drama_web/services/shot_prompts.py`
- Create: `ai_drama_web/routers/shot_prompts.py`
- Modify: `ai_drama_web/app.py`
- Create: `tests/web/test_shot_prompt_api.py`

- [ ] **Step 1: Write failing tests**

Cover blocked-by-assets, generation, manual edit, mark-ready, and Agnes request preview.

- [ ] **Step 2: Implement readiness rules**

Reject ready when canonical validation fails, requirements are not ready, an asset is missing/not usable, or duration is outside 5–15 seconds. Store readiness outside canonical content keyed by revision and shot ID.

- [ ] **Step 3: Add routes, verify, commit**

```text
POST /api/chapters/{chapter_id}/shot-prompts/generate
GET  /api/chapters/{chapter_id}/shot-prompts/revisions
PUT  /api/shot-prompt-revisions/{revision_id}
POST /api/shot-prompt-revisions/{revision_id}/shots/{shot_id}/regenerate
POST /api/shot-prompt-revisions/{revision_id}/shots/{shot_id}/mark-ready
GET  /api/shot-prompt-revisions/{revision_id}/shots/{shot_id}/agnes-preview
```

```bash
python3 -m pytest tests/web/test_shot_prompt_api.py -q
git add ai_drama_web tests/web/test_shot_prompt_api.py
git commit -m "feat: add shot prompt product workflow"
```

### Task 12: Implement Profiles and Assets UI

**Files:**
- Create: `web/src/features/assets/ProfilesAssetsTab.tsx`
- Create: `web/src/features/assets/ProfileEditor.tsx`
- Create: `web/src/features/assets/AssetGrid.tsx`
- Create: `web/src/features/assets/AssetUpload.tsx`
- Create: `web/src/features/assets/AssetGenerator.tsx`
- Create: `web/src/features/assets/api.ts`
- Create: `web/src/features/assets/ProfilesAssetsTab.test.tsx`
- Modify: `web/src/features/chapter/ChapterWorkspace.tsx`

- [ ] **Step 1: Write failing tests**

Test profile create, upload, Agnes image request, usable/rejected state, and binding.

- [ ] **Step 2: Implement visual-first grid**

Show thumbnail, type, binding, status, source, and primary action; metadata in a drawer.

- [ ] **Step 3: Verify and commit**

```bash
npm --prefix web run test -- --run
git add web/src
git commit -m "feat: add profiles and asset studio ui"
```

### Task 13: Implement Asset Requirements and Prompt UI

**Files:**
- Create: `web/src/features/prompts/ShotPromptTab.tsx`
- Create: `web/src/features/prompts/ShotPromptEditor.tsx`
- Create: `web/src/features/prompts/AssetRequirementPanel.tsx`
- Create: `web/src/features/prompts/api.ts`
- Create: `web/src/features/prompts/ShotPromptTab.test.tsx`
- Modify: `web/src/features/chapter/ChapterWorkspace.tsx`

- [ ] **Step 1: Write failing tests**

Test analysis display, blocked shot, generate all, edit one, regenerate one, and mark ready.

- [ ] **Step 2: Implement editor**

Expose positive/negative prompt, continuity, and Agnes parameters; show source storyboard shot read-only.

- [ ] **Step 3: Verify and commit**

```bash
npm --prefix web run test -- --run
git add web/src
git commit -m "feat: add asset requirements and prompt studio ui"
```

### Task 14: Add Milestone 2 verification

**Files:**
- Create: `tools/verify_m2_assets_prompts.py`
- Create: `web/tests/m2-assets-prompts.spec.ts`
- Modify: `README.md`

- [ ] **Step 1: Add backend verifier**

Use fake Agnes image backend and mock Shot Prompt runtime. Extend chapter status derivation through `assets_incomplete`, `assets_ready`, `prompts_draft`, and `prompts_ready`. Print `M2_ASSETS_SHOT_PROMPTS_PASS`.

- [ ] **Step 2: Add browser flow**

Create profiles, upload/generate assets, analyze requirements, generate prompts, and mark one ready.

- [ ] **Step 3: Run gate and commit**

```bash
python3 tools/verify_m2_assets_prompts.py
python3 migration/tools/verify_migration.py
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q
npm --prefix web run test -- --run
npm --prefix web run build
git add tools web/tests README.md
git commit -m "test: verify asset and shot prompt milestone"
```
