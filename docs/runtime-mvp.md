# Script Skill Runtime MVP

This repository includes a local, single-user runtime for the migrated script adaptation skill.

## Commands

Validate the active skill package:

```bash
python3 -m ai_drama_runtime.cli skills validate \
  --skill-root skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4
```

Run the Shengsi acceptance corpus with the deterministic mock runtime:

```bash
python3 -m ai_drama_runtime.cli run \
  --skill-root skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4 \
  --acceptance-root acceptance/shengsi-chapter-001 \
  --runtime mock \
  --model mock-script-v1
```

Script-approve and export a revision:

```bash
python3 -m ai_drama_runtime.cli approve REVISION_ID --reviewer local-user
python3 -m ai_drama_runtime.cli export shengsi-chapter-001 --output runtime-data/approved-script.md
```

The runtime persists SQLite metadata under `runtime-data/runtime.db` and immutable content objects under `runtime-data/objects` by default. It records run provenance, revision hashes, validator results, script approval/rejection records, and export records. The acceptance reference output `approved-script.md` is loaded only as reference material and is excluded from runtime requests. Script approval does not authorize downstream execution.
