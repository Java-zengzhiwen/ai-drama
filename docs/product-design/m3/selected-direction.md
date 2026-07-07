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
- Keep blocked shots visible with inline reasons.
- Prevent duplicate submission in the UI.
- Keep polling, RPM, and restart recovery hints visible near the table.
- Preview video results without autoplay.
- Preserve all result versions and mark one current adopted result.
- Keep rerun as an explicit drawer with approved override fields only.
- Always show source Prompt, source assets, Job, and attempt context for reruns.
- Do not introduce LibTV, post-production, timeline, export, or collaboration UI.
