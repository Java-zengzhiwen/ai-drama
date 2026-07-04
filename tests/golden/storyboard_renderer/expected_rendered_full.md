# Storyboard Canonical Render

schema_version: storyboard-canonical-v1
project_id: project-demo
chapter_id: chapter-001
source_script_revision_id: script-revision-001
source_script_artifact_id: script-demo
source_script_content_hash: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb

## Scene SCENE_001

- scene_order: 1
- source_scene_reference: 1-1
- location: study
- time: night
- interior_exterior: interior
- characters: CHAR_A, CHAR_B
- summary: Character A confronts Character B with the account book.

### Shot SHOT_001

- scene_id: SCENE_001
- shot_order: 1
- source_scene_reference: 1-1
- duration_seconds: 10
- shot_size: close
- camera_angle: slight_high
- camera_movement: {'type': 'push_in', 'intensity': 'slow'}
- visual_composition.framing: tight two-shot across the account book
- visual_composition.subject_focus: CHAR_A
- visual_composition.background_relation: lamp and ledger stay visible
- visual_composition.screen_direction: left_to_right
- character_positions:
  - CHAR_A | left | foreground | leaning over the table | facing=right
  - CHAR_B | right | midground | seated | facing=left
- character_actions:
  - 1 | CHAR_A | places the account book on the table
  - 2 | CHAR_B | looks away from the marked page
- emotion_performance:
  - CHAR_A | controlled anger | high | voice held low
- dialogue:
  - CHAR_A | lip_sync=true | 账不会骗人。
- sound_notes:
  - paper slides
  - distant night watch
- continuity_in.must_preserve: lamp position, account book
- continuity_in.must_change: []
- continuity_in.source_unit_or_shot_id: null
- continuity_out.must_preserve: account book
- continuity_out.must_change: CHAR_B eye line
- continuity_out.source_unit_or_shot_id: SHOT_000
