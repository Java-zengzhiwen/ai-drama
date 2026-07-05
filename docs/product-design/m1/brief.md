# M1 Product Design Brief

## Scope

Design Sprint 0 covers Milestone 1 only: project list, project board, chapter workspace, source novel tab, script tab, storyboard tab, progress navigation, common states, and the script/storyboard confirmation gates.

Out of scope: assets, Shot Prompt, Agnes generation, video results, rerun workflows, LibTV, backend implementation, database changes, API changes, and production frontend code.

## User Goal

A local single user can move one chapter from source text to approved script to approved Canonical Storyboard without losing revision, validation, or blocking context.

## Product Shape

The selected visual direction is **Storyboard Command Table**:

- left project/chapter rail for navigation and chapter status;
- top workflow rail for gate progress;
- central tabbed chapter workspace;
- spreadsheet-like storyboard editor for Canonical Storyboard fields;
- right inspector for selected shot, QC, revision metadata, and approval actions.

## Primary Flow

1. Open project list.
2. Open a project board.
3. Select a chapter.
4. Paste or review source text.
5. Generate, edit, validate, and confirm script.
6. Generate, edit, validate, and confirm storyboard.
7. Stop at the M1 boundary.

## Hard Gates

- If the script is not approved, storyboard generation and confirmation are blocked.
- If the storyboard is not approved, later production steps remain locked and are not designed in detail for M1.

## Prototype

Open the static prototype:

`docs/product-design/m1/assets/prototype.html`

Reference image:

`docs/product-design/m1/assets/selected-direction-storyboard-command-table.png`
