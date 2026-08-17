from sagri.config import ProjectConfig
from sagri.local_api.server import LocalAPI

LOCAL_API_HOST = "0.0.0.0"

# esp_cam_receiver.py already uses port 5000.
LOCAL_API_PORT = 8000


def main() -> None:
    config = ProjectConfig.from_env()

    local_api = LocalAPI(config)
    local_api.run(host=LOCAL_API_HOST, port=LOCAL_API_PORT)


if __name__ == "__main__":
    main()
