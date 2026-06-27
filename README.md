# AI Drama Skill Runtime

Local, single-user, CLI-first runtime for the migrated Script Adaptation skill.

Current execution profile: `markdown-script-mvp-v1`.

## MVP Scope

- Discover and validate local Skill Packages through `skill-id@version`.
- Run the Shengsi Chapter 001 acceptance corpus with `mock` or one-shot `openai-compatible` runtime.
- Persist immutable input snapshots, normalized requests, raw responses, runs, script revisions, validator results, approvals, exports, and provenance.
- Compare revisions, approve/reject script revisions, and export the current approved script.

This profile produces only a creator-facing Markdown DramaScript revision. It does not claim to run the complete rc2.4 artifact bundle pipeline.

## Non-Goals

No web UI, API service, agent runtime, workflow engine, registry service, Storyboard, Shot Prompt, LibTV, Agnes, Jianying, queue, vector DB, PostgreSQL, Redis, LangChain, LangGraph, or CrewAI.

## Install

Python: `>=3.9` locally, target-compatible with Python 3.11+.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

Alternative:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m ai_drama_runtime.cli --help
```

The alternative installs dependencies only; use `python3 -m ai_drama_runtime.cli` instead of the `ai-drama` console script.

## Configuration

OpenAI-compatible runtime config priority:

- API key: `AI_DRAMA_API_KEY`, then `OPENAI_API_KEY`
- Base URL: `AI_DRAMA_BASE_URL`, then `OPENAI_BASE_URL`, then SDK default
- Model: CLI `--model`, then `AI_DRAMA_MODEL`, otherwise explicit error

See `.env.example`. API keys are not saved in request snapshots or printed in errors.

## Runtime Request Snapshot

The persisted request snapshot is the same normalized request object passed to the runtime adapter. It contains package hash, execution profile, system instruction, full `SKILL.md`, manifest-declared context/schema/contract files, acceptance inputs with hashes, output contract, provider/model/timeout, and no API keys or reference outputs.

## CLI

Use `--data-root` for SQLite/object storage and `--skills-root` for local package discovery.

```bash
ai-drama --skills-root skills skills list
ai-drama --skills-root skills skills show ai-drama-script-adaptation-skill@v0.6.1-rc2.4
ai-drama --skills-root skills skills validate ai-drama-script-adaptation-skill@v0.6.1-rc2.4

ai-drama run create \
  --skill ai-drama-script-adaptation-skill@v0.6.1-rc2.4 \
  --input acceptance/shengsi-chapter-001 \
  --runtime mock \
  --model mock-script-v1

ai-drama runs show RUN_ID
ai-drama artifacts list
ai-drama artifacts revisions shengsi-chapter-001
ai-drama artifacts compare LEFT_REVISION_ID RIGHT_REVISION_ID
ai-drama approvals approve REVISION_ID --reviewer local-user
ai-drama artifacts approved shengsi-chapter-001
ai-drama artifacts export-approved shengsi-chapter-001 --output runtime-data/approved.md
ai-drama approvals reject REVISION_ID --reviewer local-user
```

Export refuses to overwrite existing files unless `--force` is supplied and writes `<output>.provenance.json`.

## Exit Codes

- `0`: success
- `2`: invalid argument or input
- `3`: not found or conflict
- `4`: runtime or parse failure
- `5`: validation failure
- `6`: approval blocked

## Skill Package Contract

`skill.json` must include `package_format_version`, `skill_id`, `version`, `display_name`, `description`, `package_status`, `instructions_entry`, `context_files`, `input_types`, `output_types`, `schemas`, `contracts`, `validators`, `runtime_requirements`, `dependency_requirements`, `provenance`, and `execution_profiles`.

All declared paths must stay inside the Skill Package root. Absolute paths, `..`, and symlink escapes are rejected. Package hashes cover only declared active files.

Validator statuses:

- `PASS`
- `FAIL`
- `SKIPPED_DEPENDENCY_MISSING`
- `NOT_APPLICABLE`

Required validators that are applicable to the current execution profile must be `PASS` before approval. Required validators explicitly marked `NOT_APPLICABLE` for the current profile do not block Markdown revision approval.

See `docs/runtime-validator-matrix.md` for the markdown profile applicability matrix.

## Persistence Semantics

Runs persist provider/model/duration, request hash, per-input references and hashes, raw usage where available, stable error codes, and safe error messages. Compare output includes metadata, request hash, input hash/reference differences, validator differences, approval differences, and unified text diff.

Approval records have deterministic sequence ordering. Export provenance sidecars include the latest approval record, input references/hashes, request hash, content hash, provider/model, package hash, and export time.

## Test

```bash
python3 migration/tools/verify_migration.py
python3 -m py_compile migration/tools/verify_migration.py skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/*.py skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/runtime-validators/*.py ai_drama_runtime/*.py
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q
```

Real OpenAI-compatible smoke tests are skipped unless credentials are provided. Mock tests never call the network.

## Current Limits

The migrated Skill business validators that require a full artifact bundle are recorded as `NOT_APPLICABLE` for a single Markdown DramaScript revision. Full bundle artifacts such as JSON script, beat registry, coverage report, source-claim-audit, handoff, creator presentation, and test reports are future scope.
