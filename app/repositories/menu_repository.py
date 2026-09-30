import json
from pathlib import Path
from typing import Any


class MenuRepository:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._data: dict[str, Any] | None = None

    def load(self) -> dict[str, Any]:
        if self._data is None:
            self._data = json.loads(self.path.read_text(encoding="utf-8"))
        return self._data

    def all_items(self) -> list[dict[str, Any]]:
        return self.load().get("items", [])
