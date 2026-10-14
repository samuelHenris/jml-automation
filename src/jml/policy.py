from __future__ import annotations

from pathlib import Path

import yaml


class Policy:
    """Role-to-access mapping. Access is data, not code.

    A user's groups = defaults + department groups + title groups.
    Unknown departments or titles get only what they match (least privilege).
    """

    def __init__(self, defaults: list[str], departments: dict):
        self.defaults = set(defaults)
        self.departments = departments

    @classmethod
    def from_yaml(cls, path: str | Path) -> Policy:
        with open(path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        defaults = (raw.get("defaults") or {}).get("groups", [])
        return cls(defaults, raw.get("departments") or {})

    def groups_for(self, department: str, title: str) -> set[str]:
        groups = set(self.defaults)
        dept = self.departments.get(department) or {}
        groups.update(dept.get("groups") or [])
        groups.update((dept.get("titles") or {}).get(title) or [])
        return groups

    @property
    def managed_groups(self) -> set[str]:
        """Every group this tool is allowed to add or remove.

        Groups outside this set are never touched, so manual or
        other-system grants are not silently stripped.
        """
        managed = set(self.defaults)
        for dept in self.departments.values():
            managed.update(dept.get("groups") or [])
            for grp in (dept.get("titles") or {}).values():
                managed.update(grp or [])
        return managed
