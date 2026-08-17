from pathlib import Path

from sagri.config import ProjectConfig
from sagri.storage.jsonl_store import JsonlAppendStore


class SensorDataRepository:
    """Persists sensor packets received from the ESP32 serial link."""

    def __init__(self, config: ProjectConfig):
        self._store = JsonlAppendStore(config.sensor_output_file)

    def save(self, sensor_packet: dict) -> Path:
        """Save one sensor data packet as one JSON line."""

        return self._store.append(sensor_packet)
