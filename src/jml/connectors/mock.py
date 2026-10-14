from __future__ import annotations

import json
from pathlib import Path

from ..models import Account
from .base import Connector


class JsonDirectory(Connector):
    """A directory kept in a JSON file. Lets the whole pipeline run offline."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._accounts: dict[str, Account] = {}
        if self.path.exists():
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self._accounts = {k: Account.from_dict(v) for k, v in raw.items()}

    def list_accounts(self) -> dict[str, Account]:
        return self._accounts

    def create_account(self, account: Account) -> None:
        if account.employee_id in self._accounts:
            raise ValueError(f"account {account.employee_id} already exists")
        self._accounts[account.employee_id] = account

    def update_attributes(self, employee_id: str, attrs: dict) -> None:
        acc = self._accounts[employee_id]
        for key, value in attrs.items():
            setattr(acc, key, value)

    def add_groups(self, employee_id: str, groups: list[str]) -> None:
        acc = self._accounts[employee_id]
        acc.groups = sorted(set(acc.groups) | set(groups))

    def remove_groups(self, employee_id: str, groups: list[str]) -> None:
        acc = self._accounts[employee_id]
        acc.groups = sorted(set(acc.groups) - set(groups))

    def set_enabled(self, employee_id: str, enabled: bool) -> None:
        self._accounts[employee_id].enabled = enabled

    def commit(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v.to_dict() for k, v in sorted(self._accounts.items())}
        self.path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
