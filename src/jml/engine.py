from __future__ import annotations

from datetime import date

from .audit import AuditLog
from .connectors.base import Connector
from .diff import compute_actions
from .models import CREATE, DISABLE, ENABLE, MOVE, ORPHAN, SYNC, Account, Action, Employee
from .policy import Policy


class SafetyGuardError(Exception):
    """Too many accounts would be disabled in one run."""


def check_leaver_guard(actions: list[Action], accounts: dict[str, Account],
                       max_pct: float) -> None:
    enabled = sum(1 for a in accounts.values() if a.enabled)
    leavers = sum(1 for a in actions if a.kind == DISABLE)
    if enabled and (leavers / enabled) * 100 > max_pct:
        raise SafetyGuardError(
            f"{leavers} of {enabled} enabled accounts would be disabled "
            f"(limit {max_pct:g}%). Check the HR feed, or re-run with a higher limit."
        )


def plan(employees: list[Employee], connector: Connector, policy: Policy,
         today: date, max_leavers_pct: float = 20.0) -> list[Action]:
    accounts = connector.list_accounts()
    actions = compute_actions(employees, accounts, policy, today)
    check_leaver_guard(actions, accounts, max_leavers_pct)
    return actions


def apply_actions(actions: list[Action], connector: Connector) -> None:
    for a in actions:
        d = a.details
        if a.kind == CREATE:
            connector.create_account(Account(**d["attrs"], enabled=True, groups=[]))
            connector.add_groups(a.employee_id, d["add_groups"])
        elif a.kind == DISABLE:
            connector.remove_groups(a.employee_id, d["remove_groups"])
            connector.set_enabled(a.employee_id, False)
        elif a.kind in (MOVE, SYNC, ENABLE):
            if a.kind == ENABLE:
                connector.set_enabled(a.employee_id, True)
            if d["attrs"]:
                connector.update_attributes(a.employee_id, d["attrs"])
            if d["add_groups"]:
                connector.add_groups(a.employee_id, d["add_groups"])
            if d["remove_groups"]:
                connector.remove_groups(a.employee_id, d["remove_groups"])
        elif a.kind == ORPHAN:
            pass  # report only
    connector.commit()


def run(employees: list[Employee], connector: Connector, policy: Policy,
        today: date, audit: AuditLog, apply: bool = False,
        max_leavers_pct: float = 20.0) -> list[Action]:
    actions = plan(employees, connector, policy, today, max_leavers_pct)
    for a in actions:
        audit.record(a)
    if apply:
        apply_actions(actions, connector)
    return actions
