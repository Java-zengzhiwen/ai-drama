#!/usr/bin/env python3
from __future__ import annotations

from common_canonical import run_validator


def validate(data, module):
    module.validate_storyboard_canonical(data)
    return {"canonical_hash": module.canonical_storyboard_hash(data)}


if __name__ == "__main__":
    raise SystemExit(run_validator("storyboard_canonical_schema", validate))
