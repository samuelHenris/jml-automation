from __future__ import annotations

from datetime import date

from .models import (
    CREATE,
    DISABLE,
    ENABLE,
    MOVE,
    ORPHAN,
    SYNC,
    Account,
    Action,
    Employee,
)
from .policy import Policy


def _attrs(emp: Employee) -> dict:
    return {
        "display_name": emp.display_name,
        "email": emp.email,
        "department": emp.department,
        "title": emp.title,
    }


def _delta(emp: Employee, acc: Account, policy: Policy) -> tuple[list, list, dict]:
    """What must change for `acc` to match what HR + policy say it should be."""
    desired = policy.groups_for(emp.department, emp.title)
    current = set(acc.groups)
    add = sorted(desired - current)
    # Only groups this tool manages may be removed (leave manual grants alone).
    remove = sorted((current & policy.managed_groups) - desired)
    changes = {k: v for k, v in _attrs(emp).items() if getattr(acc, k) != v}
    return add, remove, changes


def compute_actions(
    employees: list[Employee],
    accounts: dict[str, Account],
    policy: Policy,
    today: date,
) -> list[Action]:
    """Compare HR state to directory state and return the actions needed.

    Pure function: no I/O, no side effects. Running it against an already
    reconciled directory returns an empty list (idempotent).
    """
    actions: list[Action] = []
    hr_ids = {e.employee_id for e in employees}

    for emp in sorted(employees, key=lambda e: e.employee_id):
        acc = accounts.get(emp.employee_id)
        active = emp.is_active(today)

        if acc is None:
            if active:  # Joiner. Never create accounts for people already gone.
                actions.append(Action(
                    CREATE, emp.employee_id, emp.username,
                    {
                        "attrs": {"employee_id": emp.employee_id,
                                  "username": emp.username, **_attrs(emp)},
                        "add_groups": sorted(policy.groups_for(emp.department, emp.title)),
                    },
                ))
            continue

        if not active:
            if acc.enabled:  # Leaver.
                actions.append(Action(
                    DISABLE, emp.employee_id, acc.username,
                    {"remove_groups": sorted(acc.groups),
                     "end_date": str(emp.end_date) if emp.end_date else None},
                ))
            continue

        add, remove, changes = _delta(emp, acc, policy)

        if not acc.enabled:  # Rehire.
            actions.append(Action(
                ENABLE, emp.employee_id, acc.username,
                {"add_groups": add, "remove_groups": remove, "attrs": changes},
            ))
        elif add or remove or changes:
            moved = "department" in changes or "title" in changes
            details = {"add_groups": add, "remove_groups": remove, "attrs": changes}
            if moved:
                details["from"] = {"department": acc.department, "title": acc.title}
                details["to"] = {"department": emp.department, "title": emp.title}
            actions.append(Action(
                MOVE if moved else SYNC, emp.employee_id, acc.username, details,
            ))

    # Accounts HR has never heard of: flag for a human, never auto-act.
    for emp_id, acc in sorted(accounts.items()):
        if emp_id not in hr_ids and acc.enabled:
            actions.append(Action(ORPHAN, emp_id, acc.username,
                                  {"note": "enabled account with no HR record"}))
    return actions
