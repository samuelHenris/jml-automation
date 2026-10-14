from datetime import date

from conftest import make_emp
from jml.diff import compute_actions
from jml.models import CREATE, DISABLE, ENABLE, MOVE, ORPHAN, SYNC, Account


def acct_for(emp, policy, **overrides):
    base = {
        "employee_id": emp.employee_id,
        "username": emp.username,
        "display_name": emp.display_name,
        "email": emp.email,
        "department": emp.department,
        "title": emp.title,
        "enabled": True,
        "groups": sorted(policy.groups_for(emp.department, emp.title)),
    }
    base.update(overrides)
    return Account(**base)


def test_joiner_is_created_with_policy_groups(policy, today):
    emp = make_emp()
    (a,) = compute_actions([emp], {}, policy, today)
    assert a.kind == CREATE
    assert set(a.details["add_groups"]) == policy.groups_for("Engineering", "Software Engineer")


def test_no_account_created_for_already_terminated(policy, today):
    emp = make_emp(status="terminated", end=date(2026, 1, 1))
    assert compute_actions([emp], {}, policy, today) == []


def test_mover_gains_new_and_loses_old_access(policy, today):
    old = make_emp(dept="Engineering", title="Software Engineer")
    acc = acct_for(old, policy)
    moved = make_emp(dept="Finance", title="Financial Analyst")
    (a,) = compute_actions([moved], {moved.employee_id: acc}, policy, today)
    assert a.kind == MOVE
    assert {"dev-tools", "eng-all", "github-users"} <= set(a.details["remove_groups"])
    assert {"fin-all", "fin-reporting"} <= set(a.details["add_groups"])
    assert "all-staff" not in a.details["remove_groups"]


def test_manual_group_is_never_removed(policy, today):
    emp = make_emp()
    acc = acct_for(emp, policy)
    acc.groups = sorted(acc.groups + ["some-manual-group"])
    assert compute_actions([emp], {emp.employee_id: acc}, policy, today) == []


def test_leaver_is_disabled_and_stripped(policy, today):
    emp = make_emp(status="terminated", end=date(2026, 10, 1))
    acc = acct_for(make_emp(), policy)
    (a,) = compute_actions([emp], {emp.employee_id: acc}, policy, today)
    assert a.kind == DISABLE
    assert set(a.details["remove_groups"]) == set(acc.groups)


def test_future_end_date_is_not_disabled_yet(policy, today):
    emp = make_emp(status="terminated", end=date(2026, 12, 31))
    acc = acct_for(emp, policy)
    assert compute_actions([emp], {emp.employee_id: acc}, policy, today) == []


def test_terminated_without_end_date_is_disabled_immediately(policy, today):
    emp = make_emp(status="terminated", end=None)
    acc = acct_for(emp, policy)
    (a,) = compute_actions([emp], {emp.employee_id: acc}, policy, today)
    assert a.kind == DISABLE


def test_rehire_reenables_disabled_account(policy, today):
    emp = make_emp()
    acc = acct_for(emp, policy, enabled=False, groups=[])
    (a,) = compute_actions([emp], {emp.employee_id: acc}, policy, today)
    assert a.kind == ENABLE
    assert a.details["add_groups"]


def test_policy_drift_is_corrected_as_sync(policy, today):
    emp = make_emp()
    acc = acct_for(emp, policy, groups=["all-staff"])
    (a,) = compute_actions([emp], {emp.employee_id: acc}, policy, today)
    assert a.kind == SYNC
    assert "dev-tools" in a.details["add_groups"]


def test_orphan_account_is_flagged_not_changed(policy, today):
    ghost = make_emp(emp_id="GHOST")
    acc = acct_for(ghost, policy)
    (a,) = compute_actions([make_emp()], {"GHOST": acc}, policy, today)[-1:]
    assert a.kind == ORPHAN
