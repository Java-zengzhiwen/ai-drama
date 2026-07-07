# Selected Direction

## Direction

**Generation Command + Result Preview**

## Why This Direction

The selected direction combines the clearest parts of the explored options:

- direction 1's ready-shot command table makes batch and single-shot submission easy to scan;
- direction 3's preview treatment makes result review, version selection, and rerun decisions much clearer;
- both surfaces fit the existing M1/M2 workbench language without adding a new app shell;
- the design keeps asynchronous generation state and result decisions connected without becoming a video editor.

## Source Image

```text
docs/product-design/m3/assets/selected-direction-generation-command-result-preview.png
```

## Prototype

```text
docs/product-design/m3/assets/prototype.html
```

## Locked Decisions

- Keep `Agnes 生成` and `结果与重跑` inside the existing chapter workspace.
- Use a dense generation table as the primary submit/monitoring surface.
- Unlock `Agnes 生成` from current Shot Prompt revision existence.
- Unlock `结果与重跑` from at least one `GenerationJob`.
- Keep ready and blocked shots visible with inline reasons; only ready shots can submit.
- Prevent duplicate submission in the UI.
- Keep polling, RPM, and restart recovery hints visible near the table.
- Preview video results without autoplay.
- Keep video preview at 16:9.
- Preserve all result versions and mark one current adopted result.
- Keep rerun as an explicit drawer with approved override fields only.
- Render provider parameter controls only when backend provider capability/API schema supports them.
- Reuse M2 Asset Picker for rerun asset override and store exact replacement asset IDs.
- Always show source Prompt, source assets, Job, and attempt context for reruns.
- Do not introduce LibTV, post-production, timeline, export, or collaboration UI.
