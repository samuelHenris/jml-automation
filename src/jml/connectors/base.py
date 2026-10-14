from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Account


class Connector(ABC):
    """Interface every target directory implements (mock, LDAP, Entra, ...)."""

    @abstractmethod
    def list_accounts(self) -> dict[str, Account]: ...

    @abstractmethod
    def create_account(self, account: Account) -> None: ...

    @abstractmethod
    def update_attributes(self, employee_id: str, attrs: dict) -> None: ...

    @abstractmethod
    def add_groups(self, employee_id: str, groups: list[str]) -> None: ...

    @abstractmethod
    def remove_groups(self, employee_id: str, groups: list[str]) -> None: ...

    @abstractmethod
    def set_enabled(self, employee_id: str, enabled: bool) -> None: ...

    def commit(self) -> None:
        """Persist changes if the backend needs it."""
