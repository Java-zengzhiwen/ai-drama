#!/usr/bin/env python3
from __future__ import annotations

from common_canonical import fail, require_array, require_int, require_object, run_validator


def validate(data, module):
    require_object(data, message="storyboard must be an object")
    scenes = data.get("scenes")
    shots = data.get("shots")
    require_array(scenes, message="scenes must be an array")
    require_array(shots, message="shots must be an array")
    previous_scene_order = 0
    for index, scene in enumerate(scenes):
        require_object(scene, message="scenes[%d] must be an object" % index)
        order = scene.get("scene_order")
        require_int(order, "SHOT_ORDER_INVALID", "scenes[%d].scene_order must be an integer" % index)
        if order <= previous_scene_order:
            fail("SHOT_ORDER_INVALID", "scenes[%d].scene_order must strictly increase" % index)
        previous_scene_order = order
    order_by_scene = {}
    for index, shot in enumerate(shots):
        require_object(shot, message="shots[%d] must be an object" % index)
        scene_id = shot.get("scene_id")
        order = shot.get("shot_order")
        require_int(order, "SHOT_ORDER_INVALID", "shots[%d].shot_order must be an integer" % index)
        previous = order_by_scene.get(scene_id, 0)
        if order <= previous:
            fail("SHOT_ORDER_INVALID", "shots[%d].shot_order must strictly increase in scene" % index)
        order_by_scene[scene_id] = order
        previous_action_order = 0
        actions = shot.get("character_actions")
        require_array(actions, message="shots[%d].character_actions must be an array" % index)
        for action_index, action in enumerate(actions):
            require_object(action, message="shots[%d].character_actions[%d] must be an object" % (index, action_index))
            action_order = action.get("action_order")
            require_int(action_order, "SHOT_ORDER_INVALID", "shots[%d].character_actions[%d].action_order must be an integer" % (index, action_index))
            if action_order <= previous_action_order:
                fail("SHOT_ORDER_INVALID", "shots[%d].character_actions[%d].action_order must strictly increase" % (index, action_index))
            previous_action_order = action_order


if __name__ == "__main__":
    raise SystemExit(run_validator("storyboard_shot_order", validate))
