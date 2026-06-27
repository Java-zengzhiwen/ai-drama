# Script Skill Runtime MVP

The runtime is local and CLI-first. It stores SQLite metadata under `runtime-data/runtime.db` and immutable content objects under `runtime-data/objects` by default.

Minimal mock flow:

```bash
ai-drama skills validate ai-drama-script-adaptation-skill@v0.6.1-rc2.4
ai-drama run create --skill ai-drama-script-adaptation-skill@v0.6.1-rc2.4 --input acceptance/shengsi-chapter-001 --runtime mock --model mock-script-v1
ai-drama approvals approve REVISION_ID --reviewer local-user
ai-drama artifacts export-approved shengsi-chapter-001 --output runtime-data/approved.md
```

`approved-script.md` from the acceptance corpus is reference-only. It is not included in runtime requests or model messages.
