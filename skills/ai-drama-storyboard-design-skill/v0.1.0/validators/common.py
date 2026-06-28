from pathlib import Path
import argparse
import json
import sys


def emit(status, error_code="", message="", report_path=None, **extra):
    data = {"final_status": status, "error_code": error_code, "message": message} | extra
    if report_path:
        Path(report_path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(data, ensure_ascii=False))
    sys.exit(0 if status == "pass" else 1)
