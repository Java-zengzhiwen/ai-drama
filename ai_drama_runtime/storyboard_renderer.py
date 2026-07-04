from __future__ import annotations

from .storyboard_canonical import validate_storyboard_canonical


RENDERER_ID = "storyboard-canonical-markdown-renderer"
RENDERER_VERSION = "1.0.0"


def _value(value):
    if value is None:
        return "null"
    if value == []:
        return "[]"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "[]"
    return str(value)


def _append_list(lines, label, values, formatter):
    if values:
        lines.append("- %s:" % label)
        for item in values:
            lines.append("  - %s" % formatter(item))
    else:
        lines.append("- %s: []" % label)


def render_storyboard_markdown(canonical) -> str:
    validate_storyboard_canonical(canonical)
    source = canonical["source"]
    lines = [
        "# Storyboard Canonical Render",
        "",
        "schema_version: %s" % canonical["schema_version"],
        "project_id: %s" % canonical["project_id"],
        "chapter_id: %s" % canonical["chapter_id"],
        "source_script_revision_id: %s" % source["script_revision_id"],
        "source_script_artifact_id: %s" % source["script_artifact_id"],
        "source_script_content_hash: %s" % source["script_content_hash"],
        "",
    ]
    shots_by_scene = {}
    for shot in canonical["shots"]:
        shots_by_scene.setdefault(shot["scene_id"], []).append(shot)
    for scene in canonical["scenes"]:
        lines.extend(
            [
                "## Scene %s" % scene["scene_id"],
                "",
                "- scene_order: %s" % scene["scene_order"],
                "- source_scene_reference: %s" % scene["source_scene_reference"],
                "- location: %s" % _value(scene["location"]),
                "- time: %s" % _value(scene["time"]),
                "- interior_exterior: %s" % _value(scene["interior_exterior"]),
                "- characters: %s" % _value(scene["characters"]),
                "- summary: %s" % scene["summary"],
                "",
            ]
        )
        for shot in shots_by_scene.get(scene["scene_id"], []):
            visual = shot["visual_composition"]
            lines.extend(
                [
                    "### Shot %s" % shot["shot_id"],
                    "",
                    "- scene_id: %s" % shot["scene_id"],
                    "- shot_order: %s" % shot["shot_order"],
                    "- source_scene_reference: %s" % shot["source_scene_reference"],
                    "- duration_seconds: %s" % shot["duration_seconds"],
                    "- shot_size: %s" % shot["shot_size"],
                    "- camera_angle: %s" % shot["camera_angle"],
                    "- camera_movement: %s" % _value(shot["camera_movement"]),
                    "- visual_composition.framing: %s" % visual["framing"],
                    "- visual_composition.subject_focus: %s" % visual["subject_focus"],
                    "- visual_composition.background_relation: %s" % visual["background_relation"],
                    "- visual_composition.screen_direction: %s" % _value(visual["screen_direction"]),
                ]
            )
            _append_list(
                lines,
                "character_positions",
                shot["character_positions"],
                lambda item: "%s | %s | %s | %s | facing=%s"
                % (item["character_id"], item["screen_zone"], item["depth"], item["pose"], _value(item["facing"])),
            )
            _append_list(
                lines,
                "character_actions",
                shot["character_actions"],
                lambda item: "%s | %s | %s" % (item["action_order"], item["character_id"], item["action"]),
            )
            _append_list(
                lines,
                "emotion_performance",
                shot["emotion_performance"],
                lambda item: "%s | %s | %s | %s"
                % (item["character_id"], item["emotion"], item["intensity"], _value(item["performance_note"])),
            )
            _append_list(
                lines,
                "dialogue",
                shot["dialogue"],
                lambda item: "%s | lip_sync=%s | %s"
                % (item["speaker_character_id"], str(item["lip_sync_required"]).lower(), item["text"]),
            )
            _append_list(lines, "sound_notes", shot["sound_notes"], lambda item: item)
            for name in ("continuity_in", "continuity_out"):
                continuity = shot[name]
                lines.append("- %s.must_preserve: %s" % (name, _value(continuity["must_preserve"])))
                lines.append("- %s.must_change: %s" % (name, _value(continuity["must_change"])))
                lines.append("- %s.source_unit_or_shot_id: %s" % (name, _value(continuity["source_unit_or_shot_id"])))
            lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"
