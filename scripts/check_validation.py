#!/usr/bin/env python3
"""Fail closed unless the MobilityData JSON report explicitly contains no ERROR notices."""
import json
from pathlib import Path
report_path = Path("validation/report.json")
system_path = Path("validation/system_errors.json")
if not report_path.exists() or not system_path.exists():
    raise SystemExit("Missing validator report files; release blocked")
report = json.loads(report_path.read_text(encoding="utf-8"))
system = json.loads(system_path.read_text(encoding="utf-8"))
if system not in ([], {}, None, {"notices": []}):
    raise SystemExit(f"Validator system errors: {system}")
if not isinstance(report, dict):
    raise SystemExit("Unknown validation report format")
notices = report.get("notices")
if not isinstance(notices, list):
    raise SystemExit("Missing notices list: cannot prove zero ERROR notices")
errors = [n for n in notices if str(n.get("severity", "")).upper() == "ERROR"]
if errors:
    for err in errors[:25]:
        print(err.get("code", err.get("noticeCode", err)))
    raise SystemExit(f"Validator found {len(errors)} error notices")
print(f"PASS: MobilityData reported 0 ERROR notices among {len(notices)} notice categories")
