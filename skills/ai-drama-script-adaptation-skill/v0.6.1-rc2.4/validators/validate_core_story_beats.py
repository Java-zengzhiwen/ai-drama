#!/usr/bin/env python3
from common import *

DIMENSION_FIELDS = [
    "required_event",
    "required_information",
    "required_causal_link",
    "required_relationship_state",
    "required_emotional_change",
    "body_evidence_requirement",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--beat-registry", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()
    beats = beat_list(args.beat_registry)
    if not beats:
        emit("fail", "ERR_BEAT_REGISTRY_EMPTY", "beat registry contains no beats", args.report)
    seen = set()
    for beat in beats:
        bid = beat.get("beat_id")
        if not bid:
            emit("fail", "ERR_BEAT_ID", "beat_id is required", args.report)
        if bid in seen:
            emit("fail", "ERR_BEAT_ID", "duplicate beat_id", args.report, beat_id=bid)
        seen.add(bid)
        if beat.get("importance") not in {"critical", "major", "supporting"}:
            emit("fail", "ERR_BEAT_IMPORTANCE", "invalid beat importance", args.report, beat_id=bid)
        if not beat.get("source_evidence") and not beat.get("source_evidence_refs"):
            emit("fail", "ERR_BEAT_SOURCE_EVIDENCE", "beat requires source evidence", args.report, beat_id=bid)
        if beat.get("importance") == "critical":
            missing = [field for field in DIMENSION_FIELDS if field not in beat]
            empty = [field for field in DIMENSION_FIELDS if field in beat and not str(beat.get(field, "")).strip()]
            if missing or empty:
                emit("fail", "ERR_BEAT_DIMENSION_FIELD", "critical beat requires nonempty dimensional fields", args.report, beat_id=bid, missing=missing, empty=empty)
    emit("pass", "", "core story beats valid", args.report, beat_count=len(beats), critical_count=len([b for b in beats if b.get("importance") == "critical"]))


if __name__ == "__main__":
    main()
