#!/usr/bin/env python3
from common import *


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--schema", required=True)
    ap.add_argument("--instance", required=True)
    ap.add_argument("--report", required=True)
    args=ap.parse_args()
    try:
        from importlib.metadata import version
        import jsonschema
        from jsonschema import Draft202012Validator
    except Exception as e:
        emit("fail","ERR_JSONSCHEMA_IMPORT","Install jsonschema>=4.4.0 for real Draft 2020-12 validation: "+str(e),args.report)
    implementation_path=Path(getattr(jsonschema, "__file__", "")).resolve()
    if ROOT in implementation_path.parents and "vendor" in implementation_path.parts:
        emit("fail","ERR_JSONSCHEMA_IMPORT","vendored jsonschema facades are not allowed for Draft 2020-12 validation",args.report,implementation_path=str(implementation_path))
    schema=load_json(args.schema); instance=load_json(args.instance)
    try:
        Draft202012Validator.check_schema(schema)
        validator=Draft202012Validator(schema)
        errors=sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    except Exception as e:
        emit("fail","ERR_SCHEMA_RUNTIME",str(e),args.report)
    payload_errors=[{"path":"/"+"/".join(map(str,e.path)),"message":e.message} for e in errors]
    if errors:
        emit("fail","ERR_SCHEMA_VALIDATION","schema validation failed",args.report,schema_path=args.schema,instance_path=args.instance,validation_error_count=len(errors),validation_errors=payload_errors)
    emit("pass","","schema validation passed",args.report,schema_path=args.schema,instance_path=args.instance,validation_error_count=0,validation_errors=[],validator_implementation=str(implementation_path),jsonschema_version=version("jsonschema"))
if __name__=="__main__": main()
