"""Tiny JSON-file store shared by every demo service.

Each service owns one file under demo-services/data/. Records are dicts
with a string "id" field. This is deliberately naive: no locking, whole
file rewritten on every save. Good enough for a local demo.
"""

import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


class Store:
    def __init__(self, filename: str):
        self.path = DATA_DIR / filename

    def load(self) -> list[dict]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, records: list[dict]) -> None:
        self.path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def get(self, record_id: str) -> dict | None:
        return next((r for r in self.load() if r["id"] == record_id), None)

    def next_id(self, prefix: str) -> str:
        """Return prefix + (max numeric suffix + 1), e.g. T-1043 after T-1042."""
        pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
        nums = [
            int(m.group(1))
            for r in self.load()
            if (m := pattern.match(r["id"]))
        ]
        return f"{prefix}{(max(nums) if nums else 1000) + 1}"
