# Script Skill Runtime MVP

The runtime is local and CLI-first. It stores SQLite metadata under `runtime-data/runtime.db` and immutable content objects under `runtime-data/objects` by default.

Execution profile: `markdown-script-mvp-v1`.

Supported artifact: `creator_facing_markdown_script`.

Unsupported rc2.4 bundle artifacts: JSON script, beat registry, coverage report, assumption log, conflict registry, source claim audit, handoff, creator presentation, and test reports.

Minimal mock flow:

```bash
ai-drama skills validate ai-drama-script-adaptation-skill@v0.6.1-rc2.4
ai-drama run create --skill ai-drama-script-adaptation-skill@v0.6.1-rc2.4 --input acceptance/shengsi-chapter-001 --runtime mock --model mock-script-v1
ai-drama approvals approve REVISION_ID --reviewer local-user
ai-drama artifacts export-approved shengsi-chapter-001 --output runtime-data/approved.md
```

`approved-script.md` from the acceptance corpus is reference-only. It is not included in runtime requests or model messages.

The normalized runtime request snapshot is the exact adapter input. It includes Skill instructions, manifest-declared active context/schema/contract files, input contents and hashes, output contract, and provider/model/timeout. It excludes API keys and reference outputs.

Compare includes request hash and input hash/reference differences. Export writes a provenance sidecar with latest deterministic approval record and request/input/content hashes.
