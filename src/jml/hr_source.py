from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from .models import ACTIVE, TERMINATED, Employee

REQUIRED = [
    "employee_id", "first_name", "last_name", "email",
    "department", "title", "status", "end_date",
]


class HRDataError(Exception):
    """The HR feed is malformed or unsafe to act on."""


def load_hr_csv(path: str | Path) -> list[Employee]:
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise HRDataError(f"HR file is missing columns: {', '.join(missing)}")
        employees: list[Employee] = []
        seen: set[str] = set()
        for lineno, row in enumerate(reader, start=2):
            emp_id = (row["employee_id"] or "").strip()
            if not emp_id:
                raise HRDataError(f"line {lineno}: empty employee_id")
            if emp_id in seen:
                raise HRDataError(f"line {lineno}: duplicate employee_id {emp_id}")
            seen.add(emp_id)
            status = (row["status"] or "").strip().lower()
            if status not in (ACTIVE, TERMINATED):
                raise HRDataError(f"line {lineno}: invalid status '{status}'")
            email = (row["email"] or "").strip().lower()
            if "@" not in email:
                raise HRDataError(f"line {lineno}: invalid email '{email}'")
            end_raw = (row["end_date"] or "").strip()
            try:
                end = date.fromisoformat(end_raw) if end_raw else None
            except ValueError:
                raise HRDataError(f"line {lineno}: bad end_date '{end_raw}'") from None
            employees.append(
                Employee(
                    employee_id=emp_id,
                    first_name=row["first_name"].strip(),
                    last_name=row["last_name"].strip(),
                    email=email,
                    department=row["department"].strip(),
                    title=row["title"].strip(),
                    status=status,
                    end_date=end,
                )
            )
    if not employees:
        # An empty feed would look like "everyone left". Refuse it outright.
        raise HRDataError("HR file contains no employees; refusing to continue")
    return employees
