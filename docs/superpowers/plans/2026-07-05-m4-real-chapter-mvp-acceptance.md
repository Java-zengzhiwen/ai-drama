# Milestone 4 — Real Chapter MVP Acceptance and Stabilization Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the Web MVP on one real 12–20 shot novel chapter, verify real Agnes image/video integration, fix only blocking defects, and produce the final completion report.

**Architecture:** Add a versioned real acceptance corpus, an automated fake-provider verifier, opt-in real Agnes smoke tests, and an evidence report. This milestone adds no new product modules.

**Tech Stack:** Existing MVP, pytest markers, Playwright, real Agnes credentials supplied through environment variables, Markdown/JSON reports.

---

### Task 1: Create the real chapter acceptance corpus

**Files:**
- Create: `acceptance/web-mvp-chapter-001/manifest.json`
- Create: `acceptance/web-mvp-chapter-001/source/chapter.md`
- Create: `acceptance/web-mvp-chapter-001/context/series-canon.md`
- Create: `acceptance/web-mvp-chapter-001/context/characters.md`
- Create: `acceptance/web-mvp-chapter-001/context/production-brief.md`
- Create: `acceptance/web-mvp-chapter-001/expected/acceptance-rules.json`
- Create: `tests/acceptance/test_web_mvp_corpus.py`

- [ ] **Step 1: Write corpus validation test**

Require 12–20 expected shots, at least two characters, two scenes, one key prop, and nonempty style/continuity rules.

- [ ] **Step 2: Add manifest**

```json
{
  "id": "web-mvp-chapter-001",
  "project_id": "shengsi",
  "chapter_id": "chapter-001",
  "title": "第一章",
  "expected_shot_min": 12,
  "expected_shot_max": 20,
  "required_character_ids": ["CHAR_SHEN_QINGHE", "CHAR_SHEN_QINGLIAN"],
  "required_scene_ids": ["SCENE_SHENFU_PIANTING", "SCENE_SHENFU_GUIFANG"],
  "required_prop_ids": ["PROP_TEA_CUP"]
}
```

Use user-approved real chapter material.

- [ ] **Step 3: Verify and commit**

```bash
python3 -m pytest tests/acceptance/test_web_mvp_corpus.py -q
git add acceptance tests/acceptance
git commit -m "test: add real chapter web mvp corpus"
```

### Task 2: Add deterministic fake-provider acceptance verifier

**Files:**
- Create: `tools/verify_web_mvp_acceptance.py`
- Create: `tests/acceptance/test_web_mvp_acceptance_verifier.py`

- [ ] **Step 1: Write failing subprocess test**

Assert exit code 0 and final markers.

- [ ] **Step 2: Implement workflow**

Create clean data root; import source/context; generate/approve script and storyboard; verify shot bounds; create profiles/assets; analyze requirements; generate/ready prompts; submit all shots; complete one, fail one, leave one queued; rerun failed shot; restart context; resume jobs; verify traceability and result retention.

Print:

```text
SCRIPT_APPROVED
STORYBOARD_APPROVED
ASSETS_READY
SHOT_PROMPTS_READY
GENERATION_RECOVERY_PASS
RERUN_PASS
AI_DRAMA_WEB_PRODUCTION_MVP_ACCEPTANCE_PASS
```

- [ ] **Step 3: Verify and commit**

```bash
python3 -m pytest tests/acceptance/test_web_mvp_acceptance_verifier.py -q
python3 tools/verify_web_mvp_acceptance.py \
  --data-root /tmp/ai-drama-web-mvp-acceptance \
  --acceptance-root acceptance/web-mvp-chapter-001
git add tools/verify_web_mvp_acceptance.py tests/acceptance/test_web_mvp_acceptance_verifier.py
git commit -m "test: verify full web mvp workflow"
```

### Task 3: Add opt-in real Agnes smoke tests

**Files:**
- Create: `tests/providers/test_agnes_real_smoke.py`
- Modify: `pyproject.toml`
- Create: `docs/agnes-smoke-test.md`

- [ ] **Step 1: Register marker**

```toml
[tool.pytest.ini_options]
markers = [
  "agnes_real: requires AI_DRAMA_AGNES_API_KEY and network access"
]
```

- [ ] **Step 2: Implement guarded tests**

Skip unless `AI_DRAMA_AGNES_API_KEY` and `AI_DRAMA_RUN_REAL_AGNES=1` are set. Test one text-to-image, image-to-image, image-to-video, `video_id` status query, and result persistence. Use smallest currently supported parameters and redact secrets.

- [ ] **Step 3: Document command**

```bash
AI_DRAMA_RUN_REAL_AGNES=1 \
AI_DRAMA_AGNES_API_KEY='***' \
AI_DRAMA_PUBLIC_BASE_URL='https://reachable.example' \
python3 -m pytest -m agnes_real tests/providers/test_agnes_real_smoke.py -q
```

- [ ] **Step 4: Verify skip and commit**

```bash
python3 -m pytest tests/providers/test_agnes_real_smoke.py -q
git add pyproject.toml tests/providers/test_agnes_real_smoke.py docs/agnes-smoke-test.md
git commit -m "test: add opt-in real agnes smoke coverage"
```

### Task 4: Add final browser acceptance flow

**Files:**
- Create: `web/tests/mvp-real-chapter.spec.ts`
- Modify: `web/playwright.config.ts`

- [ ] **Step 1: Implement UI flow**

Cover project, source, script, storyboard, profiles/assets, analysis, prompts, video jobs, results, and rerun. Assert gates disable later tabs.

- [ ] **Step 2: Run and commit**

```bash
npm --prefix web run test:e2e -- mvp-real-chapter.spec.ts
git add web/tests web/playwright.config.ts
git commit -m "test: cover real chapter browser workflow"
```

### Task 5: Add acceptance reporting

**Files:**
- Create: `ai_drama_web/acceptance_report.py`
- Modify: `tools/verify_web_mvp_acceptance.py`
- Create: `tests/acceptance/test_acceptance_report.py`

- [ ] **Step 1: Write deterministic report test**

Require corpus ID, revision IDs, shot count, asset readiness, job state counts, rerun count, recovery result, traceability result, known limitations, and final status.

- [ ] **Step 2: Implement output**

```text
output/web-mvp-acceptance-report.json
output/web-mvp-acceptance-report.md
```

Do not embed `environment.head` or any self-referential commit hash.

- [ ] **Step 3: Verify and commit**

```bash
python3 -m pytest tests/acceptance/test_acceptance_report.py -q
git add ai_drama_web/acceptance_report.py tools/verify_web_mvp_acceptance.py tests/acceptance/test_acceptance_report.py
git commit -m "feat: add mvp acceptance report"
```

### Task 6: Perform scope and secret audit

**Files:**
- Create: `tools/audit_mvp_scope.py`
- Create: `tests/acceptance/test_mvp_scope_audit.py`

- [ ] **Step 1: Implement forbidden-scope scanner**

Fail on unapproved subsystem indicators outside allowlisted docs/tests:

```text
libtv
jianying
topaz
redis
postgres
kubernetes
multi_tenant
billing
voice_generation
video_editor
```

- [ ] **Step 2: Implement secret scanner**

Fail on committed non-placeholder Bearer tokens or Agnes-key fixture patterns.

- [ ] **Step 3: Verify and commit**

```bash
python3 tools/audit_mvp_scope.py
python3 -m pytest tests/acceptance/test_mvp_scope_audit.py -q
git add tools/audit_mvp_scope.py tests/acceptance/test_mvp_scope_audit.py
git commit -m "test: audit mvp scope and secret safety"
```

### Task 7: Fix only blocking acceptance defects

**Files:**
- Modify: only files implicated by acceptance failures
- Create: `tests/acceptance/test_acceptance_blockers.py`

- [ ] **Step 1: Classify failures**

```text
BLOCKER
NON_BLOCKING_PRODUCT_QUALITY
PROVIDER_LIMITATION
DEFERRED_SCOPE
```

- [ ] **Step 2: Add one failing regression test per blocker to `tests/acceptance/test_acceptance_blockers.py`**

- [ ] **Step 3: Implement the smallest fix**

Do not add modules outside approved scope.

- [ ] **Step 4: Run exact gate**

```bash
python3 -m pytest tests/acceptance/test_acceptance_blockers.py -q
python3 -m pytest -q
npm --prefix web run test -- --run
python3 tools/verify_web_mvp_acceptance.py \
  --data-root /tmp/ai-drama-web-mvp-acceptance \
  --acceptance-root acceptance/web-mvp-chapter-001
```

- [ ] **Step 5: Commit each resolved batch**

```bash
git add ai_drama_runtime ai_drama_web web tests/acceptance
git commit -m "fix: resolve mvp acceptance blockers"
```

### Task 8: Run final completion gate and update docs

**Files:**
- Modify: `README.md`
- Create: `docs/web-mvp-user-guide.md`
- Create: `docs/superpowers/reports/2026-07-05-ai-drama-web-production-mvp-completion.md`

- [ ] **Step 1: Update README**

Describe implemented Web/Agnes MVP and keep LibTV/post-production deferred.

- [ ] **Step 2: Write user guide**

Document install, backend/frontend start, Agnes settings, gates, result review, rerun, backup, and limitations.

- [ ] **Step 3: Run final gate**

```bash
python3 migration/tools/verify_migration.py
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q
npm --prefix web run test -- --run
npm --prefix web run build
npm --prefix web run test:e2e -- mvp-real-chapter.spec.ts
python3 tools/audit_mvp_scope.py
python3 tools/verify_web_mvp_acceptance.py \
  --data-root /tmp/ai-drama-web-mvp-acceptance \
  --acceptance-root acceptance/web-mvp-chapter-001 \
  --output /tmp/ai-drama-web-mvp-report
git status --short
```

Expected final report:

```text
AI_DRAMA_WEB_PRODUCTION_MVP_COMPLETE
AGNES_BACKEND_OPERATIONAL
LIBTV_DEFERRED
POST_PRODUCTION_DEFERRED
```

Expected `git status --short`: no output.

- [ ] **Step 4: Commit**

```bash
git add README.md docs
git commit -m "docs: complete ai drama web production mvp"
```
