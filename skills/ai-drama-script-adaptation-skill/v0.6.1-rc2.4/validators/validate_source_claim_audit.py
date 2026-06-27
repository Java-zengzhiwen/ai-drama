#!/usr/bin/env python3
from common import *

def normalize_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()

def text_blob(value):
    if isinstance(value, dict):
        return " ".join(text_blob(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(text_blob(v) for v in value)
    return normalize_text(value)

def registry_items(data):
    items = data.get("items")
    if items is None:
        items = data.get("conflicts")
    if items is None:
        items = []
    return items

def audit_conflict_blob(item):
    keys = ["conflict_id", "claim_a", "claim_b", "selected_interpretation", "resolution_basis"]
    return " ".join(normalize_text(item.get(k)) for k in keys)

def registry_conflict_blob(item):
    keys = [
        "conflict_id",
        "claim",
        "statement_a",
        "statement_b",
        "selected_interpretation",
        "selection_reason",
        "resolution_basis",
        "impact_on_script",
        "status",
    ]
    return " ".join(text_blob(item.get(k)) for k in keys)

def conflicts_match(audit_item, registry_item):
    audit_blob = audit_conflict_blob(audit_item)
    registry_blob = registry_conflict_blob(registry_item)
    if not audit_blob or not registry_blob:
        return False
    for key in ["conflict_id", "claim_a", "claim_b", "selected_interpretation"]:
        value = normalize_text(audit_item.get(key))
        if value and value in registry_blob:
            return True
    for key in ["conflict_id", "claim", "statement_a", "statement_b", "selected_interpretation"]:
        value = text_blob(registry_item.get(key))
        if value and value in audit_blob:
            return True
    return False

def validate_registry_crosscheck(args, audit, conflicts):
    registry = load_json(args.source_conflicts)
    items = registry_items(registry)
    if not isinstance(items, list):
        emit("fail", "ERR_SOURCE_CLAIM_AUDIT_REGISTRY_FIELD", "source conflict registry items must be list", args.report)

    requiring_registry = [item for item in conflicts if item.get("requires_registry_entry") is True]
    for item in requiring_registry:
        if not any(conflicts_match(item, registry_item) for registry_item in items):
            emit(
                "fail",
                "ERR_SOURCE_CLAIM_AUDIT_REGISTRY_MISSING",
                "audit conflict requiring registry entry is missing from source conflict registry",
                args.report,
                claim_a=item.get("claim_a", ""),
                claim_b=item.get("claim_b", ""),
            )

    examined_blob = text_blob(audit.get("claims_examined", []))
    conflict_blobs = [audit_conflict_blob(item) for item in conflicts]
    for registry_item in items:
        item_blob = registry_conflict_blob(registry_item)
        if not item_blob:
            continue
        if any(conflicts_match(audit_item, registry_item) for audit_item in conflicts):
            continue
        if text_blob(registry_item.get("conflict_id")) and text_blob(registry_item.get("conflict_id")) in examined_blob:
            continue
        if text_blob(registry_item.get("selected_interpretation")) and text_blob(registry_item.get("selected_interpretation")) in examined_blob:
            continue
        if any(text_blob(registry_item.get(k)) and text_blob(registry_item.get(k)) in " ".join(conflict_blobs) for k in ["claim", "statement_a", "statement_b"]):
            continue
        emit(
            "fail",
            "ERR_SOURCE_CLAIM_AUDIT_REGISTRY_MISSING",
            "source conflict registry entry is not represented in source-claim audit",
            args.report,
            conflict_id=registry_item.get("conflict_id", ""),
        )

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-claim-audit", required=True)
    ap.add_argument("--source-conflicts")
    ap.add_argument("--report", required=True)
    args=ap.parse_args()
    data=load_json(args.source_claim_audit)
    required=["claims_examined","potential_conflicts","selected_interpretation","resolution_basis"]
    for key in required:
        if key not in data:
            emit("fail","ERR_SOURCE_CLAIM_AUDIT_FIELD","missing source-claim-audit field",args.report,field=key)
    claims=data.get("claims_examined")
    if not isinstance(claims, list) or not claims:
        emit("fail","ERR_SOURCE_CLAIM_AUDIT_EMPTY","claims_examined must be a nonempty list",args.report)
    conflicts=data.get("potential_conflicts")
    if not isinstance(conflicts, list):
        emit("fail","ERR_SOURCE_CLAIM_AUDIT_FIELD","potential_conflicts must be list",args.report)
    for item in conflicts:
        for key in ["claim_a","claim_b","selected_interpretation","resolution_basis","requires_registry_entry"]:
            if key not in item:
                emit("fail","ERR_SOURCE_CLAIM_AUDIT_FIELD","potential conflict missing field",args.report,field=key)
        if item.get("requires_registry_entry") is True and not item.get("selected_interpretation"):
            emit("fail","ERR_SOURCE_CLAIM_AUDIT_UNRESOLVED","conflict requiring registry entry needs selected interpretation",args.report)
    if conflicts and not data.get("selected_interpretation"):
        emit("fail","ERR_SOURCE_CLAIM_AUDIT_FIELD","selected_interpretation required when conflicts exist",args.report)
    if conflicts and not data.get("resolution_basis"):
        emit("fail","ERR_SOURCE_CLAIM_AUDIT_FIELD","resolution_basis required when conflicts exist",args.report)
    if args.source_conflicts:
        validate_registry_crosscheck(args, data, conflicts)
    emit("pass","","source claim audit valid",args.report,claims_examined=len(claims),potential_conflict_count=len(conflicts),source_conflict_registry_checked=bool(args.source_conflicts))
if __name__=="__main__": main()
