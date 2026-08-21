"""
One-shot ESP32-CAM connectivity test.

Unlike esp_cam_scheduler.py (which waits for the scheduled hours —
07:00/12:00/17:00 by default), this requests a photo immediately, so
you can verify the ESP32-CAM connection without waiting or faking
SAGRI_CAPTURE_HOURS. Doesn't touch the sensor receiver or local API.

Usage:
    set SAGRI_ESP_CAM_URL=http://<esp32-cam-ip>   (or export on Linux)
    python test_esp_cam.py
"""

import sys

from sagri.camera.esp_cam_client import EspCamClient
from sagri.config import DEFAULT_ESP_CAM_BASE_URL, ProjectConfig
from sagri.storage.camera_repository import CameraImageRepository


def main() -> None:
    config = ProjectConfig.from_env()

    if config.esp_cam_base_url == DEFAULT_ESP_CAM_BASE_URL:
        print("[ERROR] SAGRI_ESP_CAM_URL is not configured.")
        print("[ERROR] Set it to the ESP32-CAM's address, e.g.:")
        print("[ERROR] set SAGRI_ESP_CAM_URL=http://192.168.1.50")
        sys.exit(1)

    print("=" * 55)
    print("ESP32-CAM ONE-SHOT TEST")
    print("=" * 55)
    print(f"ESP32-CAM URL : {config.esp_cam_base_url}")
    print()

    client = EspCamClient(config.esp_cam_base_url)

    print("[TEST] Checking /health ...")
    try:
        health = client.health()
        print(f"[TEST] Health OK: {health}")
    except Exception as error:
        print(f"[TEST] Health check FAILED: {error}")
        sys.exit(1)

    print()
    print("[TEST] Requesting a capture now (/capture) ...")

    try:
        image_data, camera_id = client.capture()
    except Exception as error:
        print(f"[TEST] Capture FAILED: {error}")
        sys.exit(1)

    print(f"[TEST] Received {len(image_data)} bytes, camera_id={camera_id}")

    config.ensure_directories()
    repository = CameraImageRepository(config)
    image_path = repository.save_image(image_data, camera_id=camera_id)

    print(f"[TEST] Saved: {image_path}")
    print()
    print("[TEST] SUCCESS")


if __name__ == "__main__":
    main()
