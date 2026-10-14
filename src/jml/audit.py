from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .models import Action


class AuditLog:
    """Append-only JSON Lines log. One line per action, dry-run included."""

    def __init__(self, path: str | Path, mode: str):
        self.path = Path(path)
        self.mode = mode
        self.run_id = uuid.uuid4().hex[:12]
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, action: Action) -> None:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "run_id": self.run_id,
            "mode": self.mode,
            "action": action.kind,
            "employee_id": action.employee_id,
            "username": action.username,
            "details": action.details,
        }
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
