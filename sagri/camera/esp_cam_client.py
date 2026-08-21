import requests

from sagri.camera.image_validator import JpegImageValidator
from sagri.storage.camera_repository import DEFAULT_CAMERA_ID

DEFAULT_TIMEOUT_SECONDS = 15


class EspCamClient:
    """
    HTTP client for the ESP32-CAM camera server
    (see ESP32_CAM_HTTP_RaspberryPi_Trigger.cpp).

    The camera no longer pushes images anywhere on its own — it just
    answers GET /health and GET|POST /capture. The Pi decides when to
    call it, which is the whole point: changing the capture schedule
    only ever touches Pi-side config, never the ESP32 firmware again.
    """

    def __init__(self, base_url: str, timeout: float = DEFAULT_TIMEOUT_SECONDS):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def health(self) -> dict:
        response = requests.get(f"{self._base_url}/health", timeout=self._timeout)
        response.raise_for_status()
        return response.json()

    def capture(self):
        """
        Trigger a fresh capture. Returns (image_data: bytes, camera_id: str).
        Raises RuntimeError/ValueError on any failure.
        """

        response = requests.get(f"{self._base_url}/capture", timeout=self._timeout)

        if response.status_code != 200:
            raise RuntimeError(
                f"ESP32-CAM capture failed: HTTP {response.status_code} "
                f"{response.text}"
            )

        image_data = response.content

        if not JpegImageValidator.is_valid(image_data):
            raise ValueError("ESP32-CAM response is not a valid JPEG.")

        camera_id = response.headers.get("X-Camera-ID", DEFAULT_CAMERA_ID)

        return image_data, camera_id
