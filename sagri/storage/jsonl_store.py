import json
from pathlib import Path


class JsonlAppendStore:
    """
    Append-only JSON-Lines file.

    The one place that knows how to append a dict as a JSON line and
    read every line back, so repositories don't each reimplement it.
    """

    def __init__(self, file_path: Path):
        self._file_path = file_path

    @property
    def file_path(self) -> Path:
        return self._file_path

    def append(self, record: dict) -> Path:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

        with self._file_path.open(mode="a", encoding="utf-8") as file:
            json.dump(record, file, ensure_ascii=False)
            file.write("\n")

        return self._file_path

    def read_all(self) -> list:
        if not self._file_path.exists():
            return []

        records = []

        with self._file_path.open(mode="r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                line = line.strip()

                if not line:
                    continue

                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    print(
                        f"[WARNING] Invalid JSON at "
                        f"{self._file_path}:{line_number}"
                    )

        return records
