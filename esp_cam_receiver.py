from sagri.camera.upload_server import CameraUploadServer
from sagri.config import ProjectConfig
from sagri.storage.camera_repository import CameraImageRepository

UPLOAD_HOST = "0.0.0.0"
UPLOAD_PORT = 5000


def main() -> None:
    """Run the HTTP receiver server for ESP32-CAM."""

    config = ProjectConfig.from_env()
    config.ensure_directories()

    server = CameraUploadServer(CameraImageRepository(config))

    print("========================================")
    print("          ESP32-CAM RECEIVER")
    print("========================================")
    print(f"Image directory : {config.camera_directory}")
    print(f"Upload endpoint : http://IP_RASPBERRY:{UPLOAD_PORT}/upload")
    print("Press Ctrl+C to stop the program.")
    print("========================================")

    server.run(host=UPLOAD_HOST, port=UPLOAD_PORT)


if __name__ == "__main__":
    main()
