from datetime import date
from pathlib import Path

import pytest

from jml.models import Employee
from jml.policy import Policy

ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 10, 14)


@pytest.fixture
def policy():
    return Policy.from_yaml(ROOT / "config" / "roles.yaml")


@pytest.fixture
def today():
    return TODAY


def make_emp(emp_id="E1", dept="Engineering", title="Software Engineer",
             status="active", end=None, first="Test", last="User"):
    return Employee(emp_id, first, last, f"{first}.{last}.{emp_id}@example.com".lower(),
                    dept, title, status, end)
