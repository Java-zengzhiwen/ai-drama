# AI Drama Storyboard Design Skill v0.1.0

## Purpose

Convert an approved drama script revision into a creator-facing storyboard revision with shot-level continuity, source coverage, and approval traceability.

## Scope

Use only for storyboard design. Do not emit shot prompts, LibTV packages, visual asset plans, image/video prompts, or execution commands.

## Required Inputs

- approved script revision
- source approval record
- `series_canon`
- `characters`
- `production_brief`

## Markdown Contract

- Top header: `# Storyboard`
- Scene header: `## 场次：{scene_id}`
- Shot header: `### 镜头 {shot_order}`
- Every shot must include:
  - `scene_id`
  - `shot_id`
  - `shot_order`
  - `source_scene_reference`
  - `duration_seconds`
  - `shot_size`
  - `camera_angle`
  - `camera_movement`
  - `visual_composition`
  - `character_positions`
  - `character_actions`
  - `emotion_performance`
  - `dialogue`
  - `sound_notes`
  - `continuity_in`
  - `continuity_out`

## Rules

- Preserve source scene order and source facts.
- Do not add new core plot events.
- Every shot duration must be 5-15 seconds.
- Every scene shot must bind a stable `source_scene_reference`.
- `shot_id` must be stable within the chapter and unique per shot.
- `shot_order` must be unique and strictly increasing within each scene.
- `continuity_in` and `continuity_out` must describe the immediate transition state.
- `character_positions`, `character_actions`, and `emotion_performance` must be explicit for every shot.
- Do not mention downstream execution artifacts or terms.

## Output

Write creator-facing Markdown storyboard only.
