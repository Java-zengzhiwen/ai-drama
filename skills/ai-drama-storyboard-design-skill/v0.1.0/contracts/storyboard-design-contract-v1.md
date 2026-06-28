# Storyboard Design Contract v1

## Structure

- Markdown only
- `# Storyboard` title
- `## 场次：{scene_id}` per scene
- `### 镜头 {shot_order}` per shot

## Required shot fields

Each shot must define:

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

## Constraints

- `duration_seconds` must be between 5 and 15.
- `shot_id` must be unique across the chapter.
- `shot_order` must be unique within a scene and increase monotonically.
- `source_scene_reference` must cover every source scene without inventing new scenes.
- No downstream execution terms, shot prompt packages, or platform parameters.

## Source binding

Storyboard revisions must cite the approved source script revision and its captured approval record in provenance.
