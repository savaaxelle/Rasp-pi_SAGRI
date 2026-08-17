import sys

from sagri.cloud.client import SagriCloudClient
from sagri.cloud.shape_projector import CloudShapeProjector
from sagri.cloud.sync_cursor_store import SyncCursorStore
from sagri.cloud.sync_worker import CloudSyncWorker
from sagri.config import ProjectConfig


def main() -> None:
    config = ProjectConfig.from_env()

    if not config.cloud_sync_enabled:
        print("[INFO] Cloud adapter is disabled (SAGRI_ENABLE_CLOUD_SYNC=0).")
        return

    if config.node_id <= 0:
        print("[ERROR] SAGRI_NODE_ID is not configured.")
        print("[ERROR] Register this Pi at https://sagri.my.id (POST /api/nodes),")
        print("[ERROR] then set: export SAGRI_NODE_ID=<the id you got back>")
        sys.exit(1)

    worker = CloudSyncWorker(
        config=config,
        client=SagriCloudClient(config.cloud_base_url),
        cursor_store=SyncCursorStore(config.cloud_sync_state_file),
        projector=CloudShapeProjector(node_id=config.node_id),
    )

    worker.run()


if __name__ == "__main__":
    main()
