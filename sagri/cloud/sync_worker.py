import time

from sagri.cloud.client import SagriCloudClient
from sagri.cloud.shape_projector import CloudShapeProjector
from sagri.cloud.sync_cursor_store import SyncCursorStore
from sagri.config import ProjectConfig
from sagri.storage.jsonl_store import JsonlAppendStore

DEFAULT_POLL_INTERVAL_SECONDS = 60

VALIDATION_ERROR_STATUS = 422


def _has_ai_values(record: dict) -> bool:
    return bool(record.get("captured_at") and record.get("image_path"))


class CloudSyncWorker:
    """
    Pushes locally collected data on to the S-AGRI cloud
    (https://sagri.my.id/api) — the "cloud-adapter" in the architecture
    diagram.

    Reads the same local JSONL files the local API reads, projects each
    new record into the cloud's field names, and POSTs one row at a
    time (the cloud contract has no batch endpoint). A SyncCursorStore
    remembers how far each of the four target tables has progressed, so
    a restart doesn't resend already-synced rows.
    """

    def __init__(
        self,
        config: ProjectConfig,
        client: SagriCloudClient,
        cursor_store: SyncCursorStore,
        projector: CloudShapeProjector,
        poll_interval: int = DEFAULT_POLL_INTERVAL_SECONDS,
    ):
        self._config = config
        self._client = client
        self._cursor_store = cursor_store
        self._projector = projector
        self._poll_interval = poll_interval

        self._sensor_store = JsonlAppendStore(config.sensor_output_file)
        self._ai_store = JsonlAppendStore(config.ai_results_file)

    def run(self) -> None:
        self._config.ensure_directories()

        print("=" * 55)
        print("S-AGRI CLOUD ADAPTER")
        print("=" * 55)
        print(f"Node ID    : {self._config.node_id}")
        print(f"Cloud URL  : {self._config.cloud_base_url}")
        print(f"Sync state : {self._config.cloud_sync_state_file}")
        print()
        print("[WAIT] Syncing local data to the cloud...")
        print()

        try:
            while True:
                self.sync_once()
                time.sleep(self._poll_interval)
        except KeyboardInterrupt:
            print()
            print("[STOP] Cloud adapter stopped by user.")

    def sync_once(self) -> None:
        targets = (
            (
                "sensor_readings",
                self._sensor_store,
                self._projector.project_sensor,
                self._projector.has_sensor_values,
                self._client.post_sensor_reading,
            ),
            (
                "weather_readings",
                self._sensor_store,
                self._projector.project_weather,
                self._projector.has_weather_values,
                self._client.post_weather_reading,
            ),
            (
                "node_status",
                self._sensor_store,
                self._projector.project_status,
                self._projector.has_status_values,
                self._client.post_node_status,
            ),
            (
                "ai_results",
                self._ai_store,
                self._projector.project_ai,
                _has_ai_values,
                self._client.post_ai_result,
            ),
        )

        for target, source_store, project, has_values, post in targets:
            try:
                self._sync_target(target, source_store, project, has_values, post)
            except Exception as error:
                print(f"[CLOUD SYNC ERROR] {target}: {error}")

    def _sync_target(self, target, source_store, project, has_values, post) -> None:
        records = source_store.read_all()
        index = self._cursor_store.get(target)

        while index < len(records):
            projected = project(records[index])

            if not has_values(projected):
                index += 1
                self._cursor_store.advance(target, index)
                continue

            success, status_code, body = post(projected)

            if success:
                index += 1
                self._cursor_store.advance(target, index)
                continue

            if status_code == VALIDATION_ERROR_STATUS:
                # Bad data — retrying won't help. Skip it, but don't
                # silently lose the failure.
                print(
                    f"[CLOUD SYNC] {target}: row {index} rejected "
                    f"(422), skipping: {body}"
                )
                index += 1
                self._cursor_store.advance(target, index)
                continue

            # Network error or 5xx: likely transient. Stop here and
            # retry this row (and everything after it) next cycle.
            print(
                f"[CLOUD SYNC] {target}: push failed "
                f"(status={status_code}), retrying next cycle: {body}"
            )
            break
