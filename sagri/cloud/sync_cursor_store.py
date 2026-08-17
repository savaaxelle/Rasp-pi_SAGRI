import json
from pathlib import Path


class SyncCursorStore:
    """
    Tracks how many lines of each source JSONL file have already been
    pushed to the cloud, per target table.

    The S-AGRI cloud API has no idempotency key, so resending an
    already-synced row creates a duplicate — this cursor is what keeps
    a restart from resending everything. Lightweight local stand-in for
    the "sync bookkeeping" the architecture diagram shows living in a
    local Postgres database.
    """

    def __init__(self, file_path: Path):
        self._file_path = file_path
        self._cursors = self._load()

    def _load(self) -> dict:
        if not self._file_path.exists():
            return {}

        try:
            with self._file_path.open(mode="r", encoding="utf-8") as file:
                data = json.load(file)
        except (json.JSONDecodeError, OSError):
            return {}

        return data if isinstance(data, dict) else {}

    def get(self, target: str) -> int:
        return int(self._cursors.get(target, 0))

    def advance(self, target: str, position: int) -> None:
        self._cursors[target] = position
        self._save()

    def _save(self) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

        with self._file_path.open(mode="w", encoding="utf-8") as file:
            json.dump(self._cursors, file, ensure_ascii=False, indent=2)
