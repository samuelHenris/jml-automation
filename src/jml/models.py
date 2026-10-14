from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date

ACTIVE = "active"
TERMINATED = "terminated"


@dataclass(frozen=True)
class Employee:
    """A record from the HR source of truth."""

    employee_id: str
    first_name: str
    last_name: str
    email: str
    department: str
    title: str
    status: str
    end_date: date | None = None

    @property
    def username(self) -> str:
        return self.email.split("@")[0].lower()

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def is_active(self, today: date) -> bool:
        """Active unless terminated AND the end date has arrived (or is missing)."""
        if self.status != TERMINATED:
            return True
        return self.end_date is not None and self.end_date > today


@dataclass
class Account:
    """An identity in the target directory."""

    employee_id: str
    username: str
    display_name: str
    email: str
    department: str
    title: str
    enabled: bool = True
    groups: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["groups"] = sorted(self.groups)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Account:
        return cls(**d)


# Action kinds, named after the lifecycle events they represent.
CREATE = "JOINER"
MOVE = "MOVER"
SYNC = "SYNC"        # drift correction (policy changed, attribute fixed)
DISABLE = "LEAVER"
ENABLE = "REHIRE"
ORPHAN = "ORPHAN"    # account with no HR record: flagged, never auto-changed


@dataclass
class Action:
    kind: str
    employee_id: str
    username: str
    details: dict = field(default_factory=dict)
