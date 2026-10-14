from __future__ import annotations

import argparse
import sys
from datetime import date

from .audit import AuditLog
from .connectors.mock import JsonDirectory
from .engine import SafetyGuardError, run
from .hr_source import HRDataError, load_hr_csv
from .models import Action
from .policy import Policy


def _fmt(a: Action) -> str:
    d = a.details
    parts = []
    if d.get("add_groups"):
        parts.append("+" + " +".join(d["add_groups"]))
    if d.get("remove_groups"):
        parts.append("-" + " -".join(d["remove_groups"]))
    if "from" in d:
        parts.append(f"({d['from']['department']}/{d['from']['title']} -> "
                     f"{d['to']['department']}/{d['to']['title']})")
    if d.get("end_date"):
        parts.append(f"(end_date {d['end_date']})")
    if d.get("note"):
        parts.append(d["note"])
    return f"[{a.kind:<6}] {a.employee_id} {a.username:<20} {' '.join(parts)}"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="jml", description="HR-driven JML automation")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sync", help="reconcile the directory with the HR feed")
    s.add_argument("--hr", required=True, help="HR CSV file")
    s.add_argument("--policy", default="config/roles.yaml")
    s.add_argument("--state", default="state/directory.json", help="mock directory file")
    s.add_argument("--audit", default="audit/jml_audit.jsonl")
    s.add_argument("--apply", action="store_true",
                   help="make changes (default is dry-run)")
    s.add_argument("--max-leavers-pct", type=float, default=20.0)
    s.add_argument("--today", type=date.fromisoformat, default=None,
                   help="override today's date (YYYY-MM-DD), useful for demos")
    args = p.parse_args(argv)

    today = args.today or date.today()
    mode = "apply" if args.apply else "dry-run"
    try:
        employees = load_hr_csv(args.hr)
        policy = Policy.from_yaml(args.policy)
        directory = JsonDirectory(args.state)
        audit = AuditLog(args.audit, mode)
        actions = run(employees, directory, policy, today, audit,
                      apply=args.apply, max_leavers_pct=args.max_leavers_pct)
    except (HRDataError, SafetyGuardError) as exc:
        print(f"ABORTED: {exc}", file=sys.stderr)
        return 2

    print(f"JML sync ({mode}), as of {today}")
    if not actions:
        print("No changes needed. Directory matches HR.")
    for a in actions:
        print(_fmt(a))
    print(f"{len(actions)} action(s). run_id={audit.run_id}")
    if not args.apply and actions:
        print("Dry-run only. Re-run with --apply to make these changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
