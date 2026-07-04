#!/usr/bin/env python3
from __future__ import annotations

from common_canonical import fail, require_array, require_int, require_object, run_validator


def validate(data, module):
    require_object(data, message="storyboard must be an object")
    shots = data.get("shots")
    require_array(shots, message="shots must be an array")
    for index, shot in enumerate(shots):
        require_object(shot, message="shots[%d] must be an object" % index)
        duration = shot.get("duration_seconds")
        require_int(duration, "STORYBOARD_DURATION_INVALID", "shots[%d].duration_seconds must be an integer" % index)
        if not 5 <= duration <= 15:
            fail("STORYBOARD_DURATION_INVALID", "shots[%d].duration_seconds must be 5-15" % index)


if __name__ == "__main__":
    raise SystemExit(run_validator("storyboard_duration", validate))
