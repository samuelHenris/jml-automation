import json
from datetime import date

import pytest

from conftest import ROOT
from jml.audit import AuditLog
from jml.connectors.mock import JsonDirectory
from jml.engine import SafetyGuardError, run
from jml.hr_source import HRDataError, load_hr_csv

DAY1 = ROOT / "data" / "hr_sample.csv"
DAY2 = ROOT / "data" / "hr_sample_day2.csv"


def sync(tmp_path, hr, policy, today, apply=True, **kw):
    state = tmp_path / "dir.json"
    audit = AuditLog(tmp_path / "audit.jsonl", "apply" if apply else "dry-run")
    return run(load_hr_csv(hr), JsonDirectory(state), policy, today, audit,
               apply=apply, **kw)


def test_dry_run_changes_nothing(tmp_path, policy, today):
    actions = sync(tmp_path, DAY1, policy, today, apply=False)
    assert len(actions) == 10
    assert not (tmp_path / "dir.json").exists()


def test_first_run_creates_everyone_then_second_run_is_noop(tmp_path, policy, today):
    assert len(sync(tmp_path, DAY1, policy, today)) == 10
    assert sync(tmp_path, DAY1, policy, today) == []


def test_day_two_produces_expected_jml_events(tmp_path, policy, today):
    sync(tmp_path, DAY1, policy, today)
    actions = sync(tmp_path, DAY2, policy, today)
    kinds = {a.employee_id: a.kind for a in actions}
    assert kinds == {"E1011": "JOINER", "E1003": "MOVER", "E1005": "LEAVER"}
    assert sync(tmp_path, DAY2, policy, today) == []  # idempotent

    directory = JsonDirectory(tmp_path / "dir.json").list_accounts()
    assert directory["E1005"].enabled is False and directory["E1005"].groups == []
    assert directory["E1006"].enabled is True           # scheduled leaver untouched
    assert "dev-tools" not in directory["E1003"].groups
    assert "fin-reporting" in directory["E1003"].groups


def test_scheduled_leaver_is_disabled_once_end_date_passes(tmp_path, policy, today):
    sync(tmp_path, DAY1, policy, today)
    sync(tmp_path, DAY2, policy, today)
    later = date(2027, 1, 2)
    actions = sync(tmp_path, DAY2, policy, later)
    assert [(a.employee_id, a.kind) for a in actions] == [("E1006", "LEAVER")]


def test_safety_guard_blocks_mass_disable(tmp_path, policy, today):
    sync(tmp_path, DAY1, policy, today)
    mass = tmp_path / "mass.csv"
    rows = ["employee_id,first_name,last_name,email,department,title,status,end_date"]
    for i in range(1001, 1011):
        rows.append(f"E{i},A,B,u{i}@example.com,IT,Helpdesk Technician,terminated,2026-01-01")
    mass.write_text("\n".join(rows) + "\n")
    with pytest.raises(SafetyGuardError):
        sync(tmp_path, mass, policy, today)
    # nothing was changed
    assert all(a.enabled for a in JsonDirectory(tmp_path / "dir.json").list_accounts().values())


def test_audit_log_records_every_action(tmp_path, policy, today):
    sync(tmp_path, DAY1, policy, today)
    lines = (tmp_path / "audit.jsonl").read_text().splitlines()
    assert len(lines) == 10
    entry = json.loads(lines[0])
    assert {"ts", "run_id", "mode", "action", "employee_id", "details"} <= entry.keys()


def test_empty_hr_feed_is_rejected(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("employee_id,first_name,last_name,email,department,title,status,end_date\n")
    with pytest.raises(HRDataError):
        load_hr_csv(empty)


def test_duplicate_ids_and_bad_status_are_rejected(tmp_path):
    hdr = "employee_id,first_name,last_name,email,department,title,status,end_date\n"
    dup = tmp_path / "dup.csv"
    dup.write_text(hdr + "E1,A,B,a@x.com,IT,T,active,\nE1,A,B,a@x.com,IT,T,active,\n")
    with pytest.raises(HRDataError):
        load_hr_csv(dup)
    bad = tmp_path / "bad.csv"
    bad.write_text(hdr + "E1,A,B,a@x.com,IT,T,maybe,\n")
    with pytest.raises(HRDataError):
        load_hr_csv(bad)
