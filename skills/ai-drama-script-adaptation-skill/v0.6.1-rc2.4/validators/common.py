#!/usr/bin/env python3
from pathlib import Path
import argparse, json, hashlib, sys, os, re, tempfile, shutil, subprocess
ROOT = Path(__file__).resolve().parents[1]
LOCAL_DEPS = ROOT / ".deps"
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))
VALID_ASSUMPTION_CLASSES = {"visual_dramatization","environment_assumption","performance_assumption","dialogue_dramatization","continuity_assumption","character_motivation_assumption","adaptation_extension"}
def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
def sha256(path):
    h=hashlib.sha256(); h.update(Path(path).read_bytes()); return h.hexdigest()
def emit(status, error_code="", message="", report_path=None, **extra):
    data={"final_status":status,"error_code":error_code,"message":message} | extra
    if report_path:
        write_json(report_path, data)
    print(json.dumps(data, ensure_ascii=False))
    sys.exit(0 if status=="pass" else 1)
def resolve(base, maybe_path):
    p=Path(maybe_path)
    return p if p.is_absolute() else Path(base)/p
def beat_list(registry):
    data=load_json(registry)
    beats=data.get("beats") or data.get("items") or []
    return beats
def critical_ids_from_registry(registry):
    return {b["beat_id"] for b in beat_list(registry) if b.get("importance")=="critical"}
def beat_ids_from_registry(registry):
    return [b["beat_id"] for b in beat_list(registry)]
def scene_ids_from_script_json(script_json):
    data=load_json(script_json)
    return [s["scene_id"] for s in data.get("scenes", [])]
def command_result(command, cwd):
    proc=subprocess.run(command, cwd=str(cwd), text=True, capture_output=True)
    try:
        payload=json.loads(proc.stdout.strip().splitlines()[-1]) if proc.stdout.strip() else {}
    except Exception:
        payload={}
    return proc, payload
def text_blob(value):
    if isinstance(value, dict):
        return " ".join(text_blob(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(text_blob(v) for v in value)
    return str(value or "")
def stale_authoritative_tokens(text):
    tokens=["pending_r1_validator_run","pending_refreshed_validation","/"+"Users/"]
    return [token for token in tokens if token in text]
def validate_authoritative_report(data, report_path, expected_version=None, label="authoritative report"):
    status=data.get("status") or data.get("final_status")
    if status in {"pending_r1_validator_run","pending_refreshed_validation","pending","stale"}:
        emit("fail","ERR_AUTHORITATIVE_STALE",label+" has pending or stale status",report_path,report_status=status)
    stale=stale_authoritative_tokens(text_blob(data))
    if stale:
        emit("fail","ERR_AUTHORITATIVE_STALE",label+" contains stale path/version markers",report_path,stale_markers=stale)
    repair_version=data.get("repair_version") or data.get("artifact_version") or data.get("script_artifact_version")
    if expected_version and repair_version and repair_version != expected_version:
        emit("fail","ERR_ARTIFACT_VERSION_MISMATCH",label+" version does not match handoff artifact_version",report_path,expected_version=expected_version,actual_version=repair_version)
def validate_current_artifact_versions(base_dir, expected_version, report_path):
    checks=[
        ("script.json","artifact_version"),
        ("coverage-report.json","script_artifact_version"),
        ("stage-result.json","artifact_version"),
    ]
    for rel,key in checks:
        p=Path(base_dir)/rel
        if not p.exists():
            continue
        data=load_json(p)
        actual=data.get(key)
        if actual and actual != expected_version:
            emit("fail","ERR_ARTIFACT_VERSION_MISMATCH","authoritative artifact version mismatch",report_path,path=rel,field=key,expected_version=expected_version,actual_version=actual)
