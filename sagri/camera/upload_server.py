from flask import Flask, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge

from sagri.camera.image_validator import JpegImageValidator
from sagri.storage.camera_repository import CameraImageRepository, DEFAULT_CAMERA_ID

# Maximum size for a single image: 5 MB.
MAX_IMAGE_SIZE = 5 * 1024 * 1024


class CameraUploadServer:
    """
    Flask HTTP server that accepts JPEG uploads from the ESP32-CAM.

    Storage and validation are injected, so the route handler stays a
    thin translation between HTTP and those collaborators.
    """

    def __init__(
        self,
        repository: CameraImageRepository,
        validator: JpegImageValidator = None,
    ):
        self._repository = repository
        self._validator = validator or JpegImageValidator()
        self.app = self._build_app()

    def _build_app(self) -> Flask:
        app = Flask(__name__)
        app.config["MAX_CONTENT_LENGTH"] = MAX_IMAGE_SIZE

        app.errorhandler(RequestEntityTooLarge)(self._handle_image_too_large)
        app.post("/upload")(self._handle_upload)

        return app

    @staticmethod
    def _handle_image_too_large(_error):
        """Send NACK when the received image exceeds the size limit."""

        return jsonify({
            "status": "NACK",
            "message": "Image size exceeds the 5 MB limit.",
        }), 413

    def _handle_upload(self):
        """Receive raw JPEG image data from ESP32-CAM via HTTP."""

        camera_id = request.headers.get("X-Camera-ID", DEFAULT_CAMERA_ID)
        image_data = request.get_data(cache=False)

        if not image_data:
            return jsonify({
                "status": "NACK",
                "message": "Image data is empty.",
            }), 400

        if not self._validator.is_valid(image_data):
            return jsonify({
                "status": "NACK",
                "message": "Received data is not a valid JPEG image.",
            }), 400

        try:
            image_path = self._repository.save_image(
                image_data=image_data,
                camera_id=camera_id,
            )
        except (OSError, ValueError) as error:
            return jsonify({
                "status": "NACK",
                "message": str(error),
            }), 500

        print(f"[IMAGE RECEIVED] {image_path}")

        return jsonify({
            "status": "ACK",
            "message": "Image successfully saved.",
            "filename": image_path.name,
        }), 200

    def run(self, host: str = "0.0.0.0", port: int = 5000) -> None:
        self.app.run(host=host, port=port, debug=False)
