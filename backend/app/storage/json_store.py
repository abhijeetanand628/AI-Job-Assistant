from __future__ import annotations

import json
import shutil
import threading
from pathlib import Path
from typing import Any


class JsonStore:
    """Small atomic JSON-file store for this single-user assessment app."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self._lock = threading.RLock()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        bundled_catalogue = Path(__file__).resolve().parents[2] / "data" / "jobs.json"
        local_catalogue = self.data_dir / "jobs.json"
        if not local_catalogue.exists() and bundled_catalogue.is_file():
            if bundled_catalogue.resolve() != local_catalogue.resolve():
                shutil.copy2(bundled_catalogue, local_catalogue)

    def read(self, name: str, default: Any) -> Any:
        path = self.data_dir / name
        with self._lock:
            if not path.exists():
                return default
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return default

    def write(self, name: str, value: Any) -> None:
        path = self.data_dir / name
        temp_path = path.with_suffix(path.suffix + ".tmp")
        with self._lock:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            temp_path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
            temp_path.replace(path)
