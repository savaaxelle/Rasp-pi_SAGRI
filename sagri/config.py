import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PROJECT_DIRECTORY = "/home/dila/projects/raspi2"

PROJECT_DIRECTORY_ENV_VAR = "SAGRI_PROJECT_DIR"

# Lets the MobileNet inference worker be switched off (e.g. while it's
# still undecided whether inference will actually be used) without
# touching any code — just set SAGRI_ENABLE_INFERENCE=0.
INFERENCE_ENABLED_ENV_VAR = "SAGRI_ENABLE_INFERENCE"
DEFAULT_INFERENCE_ENABLED = True

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
    inference_enabled: bool = DEFAULT_INFERENCE_ENABLED
    node_id: int = DEFAULT_NODE_ID
    cloud_sync_enabled: bool = DEFAULT_CLOUD_SYNC_ENABLED
    cloud_base_url: str = DEFAULT_CLOUD_BASE_URL

    @classmethod
    def from_env(cls, default: str = DEFAULT_PROJECT_DIRECTORY) -> "ProjectConfig":
        """Build a config from env vars, falling back to defaults."""

        raw_path = os.environ.get(PROJECT_DIRECTORY_ENV_VAR, default)

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

        return cls(
            project_directory=Path(raw_path),
            inference_enabled=inference_enabled,
            node_id=node_id,
            cloud_sync_enabled=cloud_sync_enabled,
            cloud_base_url=cloud_base_url,
        )

    # --------------------------------------------------------------
    # Data directories
    # --------------------------------------------------------------

    @property
    def data_directory(self) -> Path:
        return self.project_directory / "data"

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
        return self.project_directory / "models"

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

    def ensure_directories(self) -> None:
        """Create every storage directory used by the project."""

        for directory in (
            self.sensor_directory,
            self.camera_directory,
            self.ai_directory,
            self.model_directory,
        ):
            directory.mkdir(parents=True, exist_ok=True)
