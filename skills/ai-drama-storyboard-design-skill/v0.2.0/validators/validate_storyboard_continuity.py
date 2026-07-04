#!/usr/bin/env python3
from __future__ import annotations

from common_canonical import fail, run_validator


def validate(data, module):
    module.validate_storyboard_canonical(data)
    shot_ids = {shot["shot_id"] for shot in data["shots"]}
    for index, shot in enumerate(data["shots"]):
        for field in ("continuity_in", "continuity_out"):
            source_ref = shot[field].get("source_unit_or_shot_id")
            if source_ref is not None and source_ref not in shot_ids:
                fail("SHOT_MAPPING_INVALID", "shots[%d].%s references unknown shot %s" % (index, field, source_ref))


if __name__ == "__main__":
    raise SystemExit(run_validator("storyboard_continuity", validate))
