import sys

from sagri.camera.capture_schedule import CaptureSchedule
from sagri.camera.capture_scheduler import CaptureScheduler
from sagri.camera.esp_cam_client import EspCamClient
from sagri.config import DEFAULT_ESP_CAM_BASE_URL, ProjectConfig
from sagri.storage.camera_repository import CameraImageRepository


def main() -> None:
    config = ProjectConfig.from_env()

    if config.esp_cam_base_url == DEFAULT_ESP_CAM_BASE_URL:
        print("[ERROR] SAGRI_ESP_CAM_URL is not configured.")
        print("[ERROR] Set it to the ESP32-CAM's address, e.g.:")
        print("[ERROR] export SAGRI_ESP_CAM_URL=http://192.168.1.50")
        sys.exit(1)

    scheduler = CaptureScheduler(
        config=config,
        esp_cam_client=EspCamClient(config.esp_cam_base_url),
        camera_repository=CameraImageRepository(config),
        schedule=CaptureSchedule(
            config.capture_schedule_state_file,
            config.capture_schedule_hours,
        ),
    )

    scheduler.run()


if __name__ == "__main__":
    main()
