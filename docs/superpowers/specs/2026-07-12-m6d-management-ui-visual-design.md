# M6D Management UI Visual Design

**Status:** Approved by user

**Approval date:** 2026-07-12

**Selected direction:** Supplier Operations Workbench (Product Design option 1)

**Implementation status:** Not started

## Purpose

Freeze the visual target for M6D supplier, model, and project-binding management before production UI implementation. This artifact satisfies the Product Design approval gate in the M6 governance contract; it does not authorize M6D implementation before M6A-M6C are approved and their APIs are stable.

## Approved Visual Reference

```text
docs/product-design/m6d/assets/selected-direction-supplier-operations-workbench.png
```

SHA-256:

```text
364553c249be0b772a95cfaae2d6959a9ae3e086e08bd28609c657ef2ed1dabc
```

The approved image was generated from the previously selected M1-M3 Product Design references. The temporary MVP Web UI was explicitly excluded as a style source.

## Locked Visual Language

M6D inherits the existing M1-M3 workbench system:

- white professional production workspace;
- subtle `#f6f8fb` page surfaces and thin `#d9dee8` dividers;
- `#2563eb` for focus and primary actions;
- Inter/system typography with compact 14 px body copy;
- dense tables with lightweight row separation;
- small 4-8 px radii and almost no elevation;
- left navigation, central command surface, and right inspector;
- no cards-inside-cards, decorative dashboard metrics, gradients, illustrations, oversized headings, or new brand language.

## Locked Information Architecture

The primary global destination is `模型供应商`.

The supplier workspace uses three regions:

1. **Supplier list:** Agnes, OpenAI, DeepSeek, Anthropic, xAI Grok, and custom suppliers with enabled/local status.
2. **Command workspace:** selected supplier header and `配置 / 适配代码 / 模型` sections. The approved hero state is the stable model table.
3. **Inspector:** selected model identity, immutable revision, provider name, constraints, affected bindings, and conditional actions.

The model table keeps these fields visible:

- `display_name`;
- `provider_model_name`;
- capability (`text`, `image`, `video`);
- source (`built_in`, `overlay`);
- current revision;
- enabled state;
- edit/disable action.

The stable `supplier_model_id` appears in the inspector, not as the primary human-readable table label.

## Interaction And State Requirements

- `新增模型` is the primary action on the model surface.
- Editing a model saves a new immutable revision; it never silently mutates an existing revision.
- Bound-model changes show affected projects and require acknowledgement where the API contract requires it.
- Credential values remain write-only and masked.
- Local-only state is visible without becoming a dominant banner.
- ETag conflicts present an explicit reload/reconcile state and never overwrite silently.
- Built-in restore switches the current version pointer and preserves history.
- Disabled suppliers/models remain readable and clearly differentiated.
- Loading, empty, validation-error, credential-missing, runtime-unavailable, and `LOCAL_MANAGEMENT_ONLY` states reuse the existing M1-M3 status vocabulary.
- No UI control sends a real Provider test request in M6D.

## Responsive Behavior

- Desktop keeps the three-region workbench.
- At 1180 px and below, the inspector stacks below the command workspace without covering the table.
- At 768 px and below, supplier navigation becomes a compact selector/drawer, table content remains horizontally scrollable, and actions wrap without clipping.
- Dense data remains a table on supported widths; it is not converted into nested cards.

## Project Model Binding Continuation

Project model binding reuses the same visual system but remains inside the project workspace:

- capability defaults for text, image, and video;
- operation-level overrides;
- inherited versus explicit labels;
- right-side inspector for the selected binding;
- one conditional save of the complete binding set;
- a visible warning that changes affect future tasks only.

This continuation must look like the selected Supplier Operations Workbench, not like a separate settings product.

## Rejected Alternatives

- **Configuration Studio (option 2):** useful code-editor treatment, but too centered on adapter code to serve as the main supplier/model management direction. Its code editor may inform the approved direction's `适配代码` section without changing the overall layout.
- **Project Model Routing Matrix (option 3):** useful project-binding treatment, but too project-specific to define the global supplier management destination. Its routing matrix may inform the project-binding continuation without becoming the global shell.

## Approval Evidence

The user selected Product Design option 1 on 2026-07-12 with:

```text
选择1
```

Any material departure from the approved shell, hierarchy, visual tokens, or interaction model requires a revised Product Design comparison and explicit user approval before production UI changes continue.

## Implementation Gate

M6D production UI implementation may begin only when all of the following are true:

1. M6A-M6C are approved and their required APIs are stable.
2. The active M6D branch and plan are explicitly authorized.
3. The implementation uses this image and artifact as its visual target.
4. Product Design QA compares the coded UI against the approved reference at matching viewports.
5. The two mandatory read-only M6D review agents return `PASS` after implementation and verification.

