# AI Drama Skill Runtime

Local, single-user, CLI-first runtime for the migrated Script Adaptation skill and the approved Storyboard Workflow MVP.

Current execution profiles:

- `markdown-script-mvp-v1`
- `storyboard-markdown-mvp-v1`

## MVP Scope

- Discover and validate local Skill Packages through `skill-id@version`.
- Run the Shengsi Chapter 001 acceptance corpus with `mock` or one-shot `openai-compatible` runtime.
- Run Storyboard Workflow from an approved source script revision.
- Persist immutable input snapshots, normalized requests, raw responses, runs, revisions, validator results, approvals, exports, gate failures, and provenance.
- Compare revisions, approve/reject revisions, and export the current approved artifact.

This runtime does not claim to run Shot Prompt, LibTV, Agnes, or full downstream execution.

## Non-Goals

No web UI, API service, agent runtime, workflow engine, registry service, Shot Prompt, LibTV, Agnes, Jianying, queue, vector DB, PostgreSQL, Redis, LangChain, LangGraph, or CrewAI.

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

ai-drama run create \
  --skill ai-drama-storyboard-design-skill@v0.1.0 \
  --source-revision SOURCE_REVISION_ID \
  --runtime mock \
  --model mock-storyboard-v1
```

`--input` and `--source-revision` are mutually exclusive.

## Contract

Storyboard revisions require a current approved source script revision, inherited context snapshots, and storyboard validator execution before approval.

## Verification

```bash
python3 migration/tools/verify_migration.py
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q
```
