import time
from datetime import datetime

from sagri.camera.capture_schedule import CaptureSchedule
from sagri.camera.esp_cam_client import EspCamClient
from sagri.config import ProjectConfig
from sagri.storage.camera_repository import CameraImageRepository

DEFAULT_POLL_INTERVAL_SECONDS = 60


class CaptureScheduler:
    """
    Orchestrator: at each scheduled hour, ask the ESP32-CAM for a
    fresh photo and save it — the Raspberry Pi side of "B3b: POST
    /capture" from the architecture diagram. The Pi is now the one
    making the rules about when photos get taken.
    """

    def __init__(
        self,
        config: ProjectConfig,
        esp_cam_client: EspCamClient,
        camera_repository: CameraImageRepository,
        schedule: CaptureSchedule,
        poll_interval: int = DEFAULT_POLL_INTERVAL_SECONDS,
    ):
        self._config = config
        self._esp_cam_client = esp_cam_client
        self._camera_repository = camera_repository
        self._schedule = schedule
        self._poll_interval = poll_interval

    def run(self) -> None:
        self._config.ensure_directories()

        print("=" * 55)
        print("ESP32-CAM CAPTURE SCHEDULER")
        print("=" * 55)
        print(f"ESP32-CAM URL   : {self._config.esp_cam_base_url}")
        print(f"Schedule (hour) : {self._config.capture_schedule_hours}")
        print(f"Image directory : {self._config.camera_directory}")
        print()
        print("[WAIT] Waiting for the next scheduled hour...")
        print()

        try:
            while True:
                self.check_and_capture()
                time.sleep(self._poll_interval)
        except KeyboardInterrupt:
            print()
            print("[STOP] Capture scheduler stopped by user.")

    def check_and_capture(self) -> None:
        now = datetime.now()
        due_hour = self._schedule.due_hour(now)

        if due_hour is None:
            return

        print(f"[SCHEDULE] Capture due for {due_hour:02d}:00")

        try:
            image_data, camera_id = self._esp_cam_client.capture()

            image_path = self._camera_repository.save_image(
                image_data=image_data,
                camera_id=camera_id,
            )

            print(f"[SAVED] {image_path}")

            # Only mark done on success — a failure keeps retrying on
            # every poll tick for the rest of this scheduled hour.
            self._schedule.mark_captured(due_hour, now)

        except Exception as error:
            print(f"[CAPTURE ERROR] {error}")
