from pathlib import Path

from sagri.config import ProjectConfig
from sagri.storage.jsonl_store import JsonlAppendStore


class AIResultRepository:
    """Persists MobileNet inference results."""

    def __init__(self, config: ProjectConfig):
        self._store = JsonlAppendStore(config.ai_results_file)

    def save(self, result: dict) -> Path:
        return self._store.append(result)

    def load_processed_image_paths(self) -> set:
        """
        Return every image_path already present in the results file.

        Used to avoid re-running inference on images after a restart.
        """

        return {
            record["image_path"]
            for record in self._store.read_all()
            if record.get("image_path")
        }
