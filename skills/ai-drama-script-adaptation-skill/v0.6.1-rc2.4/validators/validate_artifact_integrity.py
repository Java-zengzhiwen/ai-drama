#!/usr/bin/env python3
from common import *
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--artifact-registry", required=True); ap.add_argument("--evidence-sidecar", required=True); ap.add_argument("--review-request", required=True); ap.add_argument("--base-dir", default="."); ap.add_argument("--report", required=True); args=ap.parse_args()
    base=Path(args.base_dir)
    reg=load_json(args.artifact_registry)
    for item in reg.get("artifacts", []):
        p=resolve(base, item["path"])
        if not p.exists(): emit("fail","ERR_ARTIFACT_MISSING","artifact missing",args.report,path=str(p))
        if sha256(p) != item.get("sha256"): emit("fail","ERR_HASH_MISMATCH","artifact hash mismatch",args.report,path=item["path"])
    side=load_json(args.evidence_sidecar)
    for path,digest in side.get("hashes", {}).items():
        p=resolve(base, path)
        if not p.exists() or sha256(p)!=digest: emit("fail","ERR_HASH_MISMATCH","sidecar hash mismatch",args.report,path=path)
    req=load_json(args.review_request)
    if req.get("approved_for_downstream") is not False:
        emit("fail","ERR_DOWNSTREAM_APPROVAL","review request must not approve downstream execution",args.report)
    if req.get("formal_integration_status") != "hold":
        emit("fail","ERR_FORMAL_INTEGRATION_STATUS","formal integration must remain on hold",args.report)
    handoff_path=base/"script-handoff-manifest.json"
    expected_version=None
    if handoff_path.exists():
        handoff=load_json(handoff_path)
        expected_version=handoff.get("artifact_version")
    validate_current_artifact_versions(base, expected_version, args.report)
    for rel,label in [
        ("schema-validation-report.json","schema validation report"),
        ("final-validation-report.json","final validation report"),
        ("stage-result.json","stage result"),
    ]:
        p=base/rel
        if p.exists():
            validate_authoritative_report(load_json(p), args.report, expected_version, label)
    emit("pass","","artifact integrity valid",args.report)
if __name__=="__main__": main()
