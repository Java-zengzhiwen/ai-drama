# Storyboard Workflow MVP

Storyboard Workflow MVP sits after approved script generation. It accepts one approved script revision, checks inherited context, runs storyboard validators, preserves source approval provenance, and exports fresh storyboard revisions only.

## Inputs

- approved script revision
- source approval record
- `series_canon`
- `characters`
- `production_brief`

## Gates

- the source revision must exist
- the source revision must be a drama script
- the source revision must be approved
- the source revision must be the current approved script revision
- required inherited context must exist
- the storyboard skill must be invoked with `--source-revision`

## Outputs

- storyboard revision
- validation records
- approval record
- export provenance sidecar

## Stability rules

- captured source approval stays fixed in storyboard provenance
- freshness is computed dynamically from the current approved source script revision
- stale storyboard revisions cannot be approved or exported

## CLI

```bash
ai-drama run create \
  --skill ai-drama-storyboard-design-skill@v0.1.0 \
  --source-revision SOURCE_REVISION_ID \
  --runtime mock \
  --model mock-storyboard-v1
```

## Validation

Use `docs/storyboard/storyboard-validator-matrix.md` for the current validator matrix.
