import os
from dataclasses import dataclass
from pathlib import Path

# Where the code itself lives (run_raspi_all.py, the entrypoint
# scripts, the sagri/ package) — used to find/launch the services.
#
# Auto-detected from this file's own location: sagri/config.py always
# sits at <project_root>/sagri/config.py, so its grandparent directory
# IS the project root — on this Windows laptop, on the Pi, or anywhere
# else the whole tree gets copied to. No manual setup needed; this is
# only a fallback SAGRI_PROJECT_DIR can still override when genuinely
# needed (e.g. code and a symlink/mount don't actually coincide).
DEFAULT_PROJECT_DIRECTORY = str(Path(__file__).resolve().parent.parent)

PROJECT_DIRECTORY_ENV_VAR = "SAGRI_PROJECT_DIR"

# Where data/ and models/ live. Defaults to the older raspi2 directory
# so existing data keeps being used even though the code itself has
# moved to a differently-named project directory. Can be the same
# path as PROJECT_DIRECTORY_ENV_VAR — most setups will want that.
DEFAULT_STORAGE_ROOT = "/home/dila/projects/raspi2"

STORAGE_ROOT_ENV_VAR = "SAGRI_DATA_DIR"

# Lets the MobileNet inference worker be switched off (e.g. while it's
# still undecided whether inference will actually be used) without
# touching any code — just set SAGRI_ENABLE_INFERENCE=0.
INFERENCE_ENABLED_ENV_VAR = "SAGRI_ENABLE_INFERENCE"
DEFAULT_INFERENCE_ENABLED = False

# Identity assigned by the S-AGRI cloud (POST /api/nodes) for this
# Raspberry Pi. 0 means "not configured yet" — local-only use is still
# fine, but the cloud adapter refuses to push with an unset node_id.
NODE_ID_ENV_VAR = "SAGRI_NODE_ID"
DEFAULT_NODE_ID = 0

# Off by default: this pushes real data to a public shared cloud service,
# so it should never turn on silently. Set SAGRI_ENABLE_CLOUD_SYNC=1 once
# SAGRI_NODE_ID is configured.
CLOUD_SYNC_ENABLED_ENV_VAR = "SAGRI_ENABLE_CLOUD_SYNC"
DEFAULT_CLOUD_SYNC_ENABLED = False

CLOUD_BASE_URL_ENV_VAR = "SAGRI_CLOUD_BASE_URL"
DEFAULT_CLOUD_BASE_URL = "https://sagri.my.id/api"

# ESP32-CAM now runs as a pure HTTP camera server (see
# ESP32_CAM_HTTP_RaspberryPi_Trigger.cpp) — the Pi is the one that
# decides when to call GET/POST <url>/capture. This placeholder is
# intentionally invalid so the scheduler refuses to start until it's
# set to the camera's real address.
ESP_CAM_BASE_URL_ENV_VAR = "SAGRI_ESP_CAM_URL"
DEFAULT_ESP_CAM_BASE_URL = "http://192.168.1.70"

# When the Pi should request a fresh photo. Configurable so the
# schedule can change without ever touching ESP32-CAM firmware again.
CAPTURE_SCHEDULE_HOURS_ENV_VAR = "SAGRI_CAPTURE_HOURS"
DEFAULT_CAPTURE_SCHEDULE_HOURS = "7,12,17"

_TRUTHY_VALUES = {"1", "true", "yes", "on"}
_FALSY_VALUES = {"0", "false", "no", "off"}


def _parse_bool_env(name: str, default: bool) -> bool:
    raw_value = os.environ.get(name)

    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()

    if normalized in _TRUTHY_VALUES:
        return True

    if normalized in _FALSY_VALUES:
        return False

    raise ValueError(
        f"Invalid value for {name}: {raw_value!r} "
        f"(expected one of {sorted(_TRUTHY_VALUES | _FALSY_VALUES)})"
    )


def _parse_hours(raw_value: str) -> tuple:
    try:
        hours = tuple(int(part.strip()) for part in raw_value.split(",") if part.strip())
    except ValueError:
        raise ValueError(
            f"Invalid value for {CAPTURE_SCHEDULE_HOURS_ENV_VAR}: {raw_value!r} "
            "(expected comma-separated hours, e.g. '7,12,17')"
        )

    for hour in hours:
        if not 0 <= hour <= 23:
            raise ValueError(
                f"Invalid value for {CAPTURE_SCHEDULE_HOURS_ENV_VAR}: "
                f"hour {hour} is out of range 0-23"
            )

    return hours


@dataclass(frozen=True)
class ProjectConfig:
    """
    Single source of truth for every storage path and feature toggle
    used on the Pi.

    Every collaborator in the project receives this object (or paths
    derived from it) through its constructor instead of importing shared
    globals directly, so storage location and feature toggles can change
    without touching unrelated classes.
    """

    project_directory: Path
    storage_root: Path = Path(DEFAULT_STORAGE_ROOT)
    inference_enabled: bool = DEFAULT_INFERENCE_ENABLED
    node_id: int = DEFAULT_NODE_ID
    cloud_sync_enabled: bool = DEFAULT_CLOUD_SYNC_ENABLED
    cloud_base_url: str = DEFAULT_CLOUD_BASE_URL
    esp_cam_base_url: str = DEFAULT_ESP_CAM_BASE_URL
    capture_schedule_hours: tuple = _parse_hours(DEFAULT_CAPTURE_SCHEDULE_HOURS)

    @classmethod
    def from_env(
        cls,
        default: str = DEFAULT_PROJECT_DIRECTORY,
        storage_default: str = DEFAULT_STORAGE_ROOT,
    ) -> "ProjectConfig":
        """Build a config from env vars, falling back to defaults."""

        raw_path = os.environ.get(PROJECT_DIRECTORY_ENV_VAR, default)
        raw_storage_path = os.environ.get(STORAGE_ROOT_ENV_VAR, storage_default)

        inference_enabled = _parse_bool_env(
            INFERENCE_ENABLED_ENV_VAR,
            DEFAULT_INFERENCE_ENABLED,
        )

        cloud_sync_enabled = _parse_bool_env(
            CLOUD_SYNC_ENABLED_ENV_VAR,
            DEFAULT_CLOUD_SYNC_ENABLED,
        )

        try:
            node_id = int(os.environ.get(NODE_ID_ENV_VAR, DEFAULT_NODE_ID))
        except ValueError:
            raise ValueError(
                f"Invalid value for {NODE_ID_ENV_VAR}: must be an integer"
            )

        cloud_base_url = os.environ.get(CLOUD_BASE_URL_ENV_VAR, DEFAULT_CLOUD_BASE_URL)
        esp_cam_base_url = os.environ.get(ESP_CAM_BASE_URL_ENV_VAR, DEFAULT_ESP_CAM_BASE_URL)

        capture_schedule_hours = _parse_hours(
            os.environ.get(CAPTURE_SCHEDULE_HOURS_ENV_VAR, DEFAULT_CAPTURE_SCHEDULE_HOURS)
        )

        return cls(
            project_directory=Path(raw_path),
            storage_root=Path(raw_storage_path),
            inference_enabled=inference_enabled,
            node_id=node_id,
            cloud_sync_enabled=cloud_sync_enabled,
            cloud_base_url=cloud_base_url,
            esp_cam_base_url=esp_cam_base_url,
            capture_schedule_hours=capture_schedule_hours,
        )

    # --------------------------------------------------------------
    # Data directories — rooted at storage_root, which defaults to a
    # different path than project_directory (see DEFAULT_STORAGE_ROOT
    # above) so the code can live somewhere new while data stays put.
    # --------------------------------------------------------------

    @property
    def data_directory(self) -> Path:
        return self.storage_root / "data"

    @property
    def sensor_directory(self) -> Path:
        return self.data_directory / "sensor"

    @property
    def camera_directory(self) -> Path:
        return self.data_directory / "camera"

    @property
    def ai_directory(self) -> Path:
        return self.data_directory / "ai"

    @property
    def model_directory(self) -> Path:
        return self.storage_root / "models"

    # --------------------------------------------------------------
    # Files
    # --------------------------------------------------------------

    @property
    def sensor_output_file(self) -> Path:
        return self.sensor_directory / "sensor_data.jsonl"

    @property
    def camera_metadata_file(self) -> Path:
        return self.camera_directory / "camera_metadata.jsonl"

    @property
    def ai_results_file(self) -> Path:
        return self.ai_directory / "ai_results.jsonl"

    @property
    def model_path(self) -> Path:
        return self.model_directory / "mobilenet_model.keras"

    @property
    def labels_file(self) -> Path:
        return self.model_directory / "labels.txt"

    @property
    def cloud_sync_state_file(self) -> Path:
        return self.data_directory / "cloud_sync_state.json"

    @property
    def capture_schedule_state_file(self) -> Path:
        return self.camera_directory / "capture_schedule_state.json"

    def ensure_directories(self) -> None:
        """Create every storage directory used by the project."""

        for directory in (
            self.sensor_directory,
            self.camera_directory,
            self.ai_directory,
            self.model_directory,
        ):
            directory.mkdir(parents=True, exist_ok=True)
