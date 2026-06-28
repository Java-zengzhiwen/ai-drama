# Storyboard CLI Guide

Storyboard creation uses the same `ai-drama run create` command with an explicit `--source-revision` gate.

```bash
ai-drama run create \
  --skill ai-drama-storyboard-design-skill@v0.1.0 \
  --source-revision SOURCE_REVISION_ID \
  --runtime mock \
  --model mock-storyboard-v1
```

Rules:

- `--input` and `--source-revision` are mutually exclusive.
- Script skills use `--input`.
- Storyboard skills use `--source-revision`.
- Gate failures return a stable JSON payload and exit code `2`.
- The runtime never calls the model when a gate fails.
