# Route and Screen Coverage

| Route | Product scope | Implemented screen treatment |
| --- | --- | --- |
| `/projects` | project entry | unified shell, compact creation band, dense project table |
| `/projects/:projectId` | project dashboard | chapter entry table, compact chapter creation, model-binding access |
| `/projects/:projectId/model-bindings` | adjacent M6D binding | existing behavior retained; shared shell/tokens |
| `/projects/:projectId/chapters/:chapterId` | M1–M3 production workspace | chapter identity, seven-step rail, source, script, storyboard, assets, prompts, generation, results and rerun |
| `/suppliers` | adjacent M6D supplier list | existing supplier hierarchy visually aligned |
| `/suppliers/:supplierId` | adjacent M6D supplier workbench | three-region desktop and compact supplier selector retained |
| `/settings/agnes` | legacy settings | regression only; no new Product Design decision applied |

No route was added, removed, or renamed.

## Milestone coverage

- M1: source/script revisions, storyboard command table, selected-shot inspector, QC and approval.
- M2: profiles/assets, visual asset review drawer, version/adoption evidence, requirements and Shot Prompt editing.
- M3: generation queue, request preview, result versions/current adoption, video preview and rerun composition.
- M6D: visually aligned because the implementation already existed; no supplier behavior changed.

The approved source screenshots contain broader project-tree and high-density example content that the current backend does not expose as a route-level navigation contract. The production implementation preserves the approved visual language and command-table/inspector hierarchy without fabricating production records.
