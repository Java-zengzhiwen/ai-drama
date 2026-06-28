# AI Drama Storyboard Design Skill v0.1.0

## Purpose

Convert an approved drama script revision into a creator-facing storyboard revision with shot structure, continuity, and upstream binding.

## Scope

Use only for storyboard design and storyboard approval preparation. Do not run shot prompt, visual asset, image, video, platform execution, or general workflow orchestration tasks.

## Inputs

Require an approved script revision, its source approval record, and the upstream script inputs retained by the runtime.

## Rules

- Preserve script scene order and causal flow.
- Split scenes into shots without rewriting story facts.
- Keep shot duration between 5 and 15 seconds.
- Bind every storyboard revision to the approved source script revision.
- Mark stale revisions stale when the source script approval changes.

## Output

Write creator-facing storyboard Markdown only.
