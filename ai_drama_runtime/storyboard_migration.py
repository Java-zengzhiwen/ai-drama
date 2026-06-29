from __future__ import annotations

import re

from .storyboard_canonical import canonical_storyboard_hash, serialize_canonical_json, validate_storyboard_canonical
from .storyboard_renderer import render_storyboard_markdown


class StoryboardMigrationError(ValueError):
    code = "LEGACY_MIGRATION_REQUIRES_REVIEW"


def _scene_id(index):
    return "SCENE_%03d" % index


def _shot_id(index):
    return "SHOT_%03d" % index


def _parse_legacy_shots(markdown):
    current_scene_reference = ""
    scene_order = 0
    shot_order_by_scene = {}
    scenes = []
    shots = []
    current = None
    current_fields = set()
    required_fields = {
        "source_scene_reference",
        "duration_seconds",
        "shot_size",
        "camera_angle",
        "camera_movement",
        "visual_composition",
        "character_positions",
        "character_actions",
        "emotion_performance",
        "dialogue",
        "sound_notes",
        "continuity_in",
        "continuity_out",
    }

    def _finish_current():
        if current is None:
            return
        missing = sorted(required_fields - current_fields)
        if missing:
            raise StoryboardMigrationError("legacy shot missing required fields: %s" % ",".join(missing))
        shots.append(current)
    global_shot_index = 0
    scene_id_by_ref = {}
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        scene_match = re.match(r"^##\s*(?:场次：|Scene\s*:?\s*)(.+)$", line)
        if scene_match:
            scene_order += 1
            current_scene_reference = scene_match.group(1).strip()
            scene_id_by_ref[current_scene_reference] = _scene_id(scene_order)
            scenes.append(
                {
                    "scene_id": _scene_id(scene_order),
                    "scene_order": scene_order,
                    "source_scene_reference": current_scene_reference,
                    "location": None,
                    "time": None,
                    "interior_exterior": None,
                    "characters": [],
                    "summary": "Migrated legacy scene %s" % current_scene_reference,
                }
            )
            continue
        if re.match(r"^###\s*(?:镜头|Shot)\b", line):
            if not current_scene_reference:
                raise StoryboardMigrationError("shot appears before scene")
            _finish_current()
            global_shot_index += 1
            current_fields = set()
            scene_id = scene_id_by_ref[current_scene_reference]
            shot_order_by_scene[scene_id] = shot_order_by_scene.get(scene_id, 0) + 1
            current = {
                "scene_id": scene_id,
                "shot_id": _shot_id(global_shot_index),
                "shot_order": shot_order_by_scene[scene_id],
                "source_scene_reference": current_scene_reference,
                "duration_seconds": 8,
                "shot_size": "medium",
                "camera_angle": "eye_level",
                "camera_movement": None,
                "visual_composition": {
                    "framing": "migrated legacy framing",
                    "subject_focus": "legacy subject",
                    "background_relation": "legacy background",
                    "screen_direction": None,
                },
                "character_positions": [],
                "character_actions": [],
                "emotion_performance": [],
                "dialogue": [],
                "sound_notes": [],
                "continuity_in": {"must_preserve": [], "must_change": [], "source_unit_or_shot_id": None},
                "continuity_out": {"must_preserve": [], "must_change": [], "source_unit_or_shot_id": None},
            }
            continue
        field_match = re.match(r"^-\s*([A-Za-z_]+)\s*:\s*(.*)$", line)
        if current is None or not field_match:
            continue
        key, value = field_match.group(1), field_match.group(2).strip()
        if key in required_fields:
            current_fields.add(key)
        if key == "source_scene_reference" and value:
            current["source_scene_reference"] = value
        elif key == "duration_seconds":
            try:
                current["duration_seconds"] = int(value)
            except ValueError as exc:
                raise StoryboardMigrationError("invalid duration") from exc
        elif key == "shot_size" and value:
            current["shot_size"] = value
        elif key == "camera_angle" and value:
            current["camera_angle"] = value
        elif key == "camera_movement":
            current["camera_movement"] = None if value in {"", "null", "still"} else {"type": value}
        elif key == "visual_composition" and value:
            current["visual_composition"]["framing"] = value
        elif key == "character_positions" and value:
            current["character_positions"] = [
                {
                    "character_id": "CHAR_LEGACY",
                    "screen_zone": "center",
                    "depth": "foreground",
                    "pose": value,
                    "facing": None,
                }
            ]
        elif key == "character_actions" and value:
            current["character_actions"] = [{"character_id": "CHAR_LEGACY", "action_order": 1, "action": value}]
        elif key == "emotion_performance" and value:
            current["emotion_performance"] = [
                {
                    "character_id": "CHAR_LEGACY",
                    "emotion": value,
                    "intensity": "medium",
                    "performance_note": None,
                }
            ]
        elif key == "dialogue" and value:
            current["dialogue"] = [{"speaker_character_id": "CHAR_LEGACY", "text": value, "lip_sync_required": True}]
        elif key == "sound_notes" and value:
            current["sound_notes"] = [value]
        elif key == "continuity_in" and value:
            current["continuity_in"]["must_preserve"] = [value]
        elif key == "continuity_out" and value:
            current["continuity_out"]["must_preserve"] = [value]
    if current is not None:
        _finish_current()
    if not scenes or not shots:
        raise StoryboardMigrationError("legacy storyboard lacks scenes or shots")
    return scenes, shots


def legacy_markdown_to_canonical(markdown, *, source_revision, source_artifact_id, source_content_hash):
    scenes, shots = _parse_legacy_shots(markdown)
    candidate = {
        "schema_version": "storyboard-canonical-v1",
        "project_id": source_revision.project_id,
        "chapter_id": source_revision.chapter_id,
        "source": {
            "script_artifact_id": source_artifact_id,
            "script_revision_id": source_revision.revision_id,
            "script_content_hash": source_content_hash,
        },
        "scenes": scenes,
        "shots": shots,
    }
    validate_storyboard_canonical(candidate)
    return candidate


def write_migration_preview(candidate, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    canonical_path = output_dir / "storyboard-canonical-candidate.json"
    rendered_path = output_dir / "storyboard-canonical-rendered.md"
    canonical_path.write_bytes(serialize_canonical_json(candidate))
    rendered_path.write_text(render_storyboard_markdown(candidate), encoding="utf-8")
    return {
        "status": "PREVIEW",
        "candidate_hash": canonical_storyboard_hash(candidate),
        "canonical_candidate_path": str(canonical_path),
        "rendered_markdown_path": str(rendered_path),
    }
