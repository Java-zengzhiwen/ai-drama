# Runtime MVP

The runtime is local and CLI-first. It stores SQLite metadata under `runtime-data/runtime.db` and immutable content objects under `runtime-data/objects` by default.

Execution profiles:

- `markdown-script-mvp-v1`
- `storyboard-markdown-mvp-v1`

Supported artifact types:

- `drama_script`
- `storyboard`

Minimal mock flows:

```bash
ai-drama skills validate ai-drama-script-adaptation-skill@v0.6.1-rc2.4
ai-drama run create --skill ai-drama-script-adaptation-skill@v0.6.1-rc2.4 --input acceptance/shengsi-chapter-001 --runtime mock --model mock-script-v1
ai-drama run create --skill ai-drama-storyboard-design-skill@v0.1.0 --source-revision REVISION_ID --runtime mock --model mock-storyboard-v1
ai-drama approvals approve REVISION_ID --reviewer local-user
ai-drama artifacts export-approved ARTIFACT_ID --output runtime-data/approved.md
```

The normalized runtime request snapshot is the exact adapter input. It includes Skill instructions, manifest-declared active context/schema/contract files, input contents and hashes, output contract, and provider/model/timeout. It excludes API keys and reference outputs.

Compare includes request hash and input hash/reference differences. Export writes a provenance sidecar with deterministic approval records and request/input/content hashes.
