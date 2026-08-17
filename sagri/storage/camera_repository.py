import re
from datetime import datetime
from pathlib import Path

from sagri.config import ProjectConfig
from sagri.storage.jsonl_store import JsonlAppendStore
from sagri.time_utils import utc_now_iso

DEFAULT_CAMERA_ID = "esp_cam_01"


class CameraImageRepository:
    """
    Persists JPEG images received from the ESP32-CAM and their metadata.

    Images are stored in date-partitioned directories; one metadata line
    is appended per image so other services (e.g. the inference worker)
    can discover new images without touching the filesystem layout.
    """

    def __init__(self, config: ProjectConfig):
        self._camera_directory = config.camera_directory
        self._metadata_store = JsonlAppendStore(config.camera_metadata_file)

    def save_image(
        self,
        image_data: bytes,
        camera_id: str = DEFAULT_CAMERA_ID,
    ) -> Path:
        if not image_data:
            raise ValueError("Image data is empty.")

        received_time = datetime.now()

        safe_camera_id = self._sanitize_camera_id(camera_id)

        date_directory = (
            self._camera_directory / received_time.strftime("%Y-%m-%d")
        )

        date_directory.mkdir(parents=True, exist_ok=True)

        filename = (
            f"{safe_camera_id}_"
            f"{received_time.strftime('%Y%m%d_%H%M%S_%f')}.jpg"
        )

        image_path = date_directory / filename

        image_path.write_bytes(image_data)

        metadata = {
            "camera_id": safe_camera_id,
            # UTC with an explicit offset, per the S-AGRI cloud contract
            # (a naive local timestamp would be rejected/misinterpreted).
            "raspi_received_time": utc_now_iso(),
            "filename": filename,
            "image_path": str(image_path),
            "size_bytes": len(image_data),
        }

        self._metadata_store.append(metadata)

        return image_path

    def read_all_metadata(self) -> list:
        """Read every camera metadata record saved so far."""

        return self._metadata_store.read_all()

    @staticmethod
    def _sanitize_camera_id(camera_id: str) -> str:
        """Prevent unsafe characters from being used in filenames."""

        safe_camera_id = re.sub(r"[^a-zA-Z0-9_-]", "_", camera_id).strip("_")

        return safe_camera_id or DEFAULT_CAMERA_ID
