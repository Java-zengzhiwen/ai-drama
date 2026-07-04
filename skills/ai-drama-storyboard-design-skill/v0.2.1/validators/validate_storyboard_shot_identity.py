#!/usr/bin/env python3
from __future__ import annotations

from common_canonical import fail, require_array, require_object, run_validator


def validate(data, module):
    require_object(data, message="storyboard must be an object")
    scenes = data.get("scenes")
    shots = data.get("shots")
    require_array(scenes, message="scenes must be an array")
    require_array(shots, message="shots must be an array")
    seen_scenes = set()
    for index, scene in enumerate(scenes):
        require_object(scene, message="scenes[%d] must be an object" % index)
        scene_id = scene.get("scene_id")
        if not isinstance(scene_id, str) or not module.SCENE_ID_RE.match(scene_id):
            fail("SHOT_ID_INVALID", "scenes[%d].scene_id is invalid" % index)
        if scene_id in seen_scenes:
            fail("SHOT_ID_INVALID", "scenes[%d].scene_id is duplicated" % index)
        seen_scenes.add(scene_id)
    seen_shots = set()
    for index, shot in enumerate(shots):
        require_object(shot, message="shots[%d] must be an object" % index)
        shot_id = shot.get("shot_id")
        if not isinstance(shot_id, str) or not module.SHOT_ID_RE.match(shot_id):
            fail("SHOT_ID_INVALID", "shots[%d].shot_id is invalid" % index)
        if shot_id in seen_shots:
            fail("SHOT_ID_INVALID", "shots[%d].shot_id is duplicated" % index)
        seen_shots.add(shot_id)


if __name__ == "__main__":
    raise SystemExit(run_validator("storyboard_shot_identity", validate))
