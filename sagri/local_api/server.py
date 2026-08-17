from datetime import datetime, timedelta, timezone

from flask import Flask, jsonify, request, send_from_directory

from sagri.cloud.shape_projector import CloudShapeProjector
from sagri.config import ProjectConfig
from sagri.storage.jsonl_store import JsonlAppendStore

DEFAULT_HISTORY_LIMIT = 100
MAX_HISTORY_LIMIT = 1000


class LocalAPI:
    """
    Local read-only REST API for the Raspberry Pi.

    The serial receiver, camera receiver, and inference worker remain
    the data writers. This API exposes their local JSONL data to LAN
    clients using S-AGRI-like endpoint names and cloud-compatible field
    names (via CloudShapeProjector) — "works with zero internet" per
    the architecture diagram, since it never talks to the cloud itself.
    """

    def __init__(self, config: ProjectConfig):
        self._config = config

        self.sensor_store = JsonlAppendStore(config.sensor_output_file)
        self.ai_store = JsonlAppendStore(config.ai_results_file)

        self.projector = CloudShapeProjector(node_id=config.node_id)

        self.app = Flask(__name__)
        self._register_routes()

    # ========================================================
    # UTILITIES
    # ========================================================

    @staticmethod
    def _parse_limit():
        value = request.args.get("limit", str(DEFAULT_HISTORY_LIMIT))

        try:
            limit = int(value)
        except ValueError:
            limit = DEFAULT_HISTORY_LIMIT

        return max(1, min(limit, MAX_HISTORY_LIMIT))

    @staticmethod
    def _parse_datetime(value):
        if not value:
            return None

        text = str(value).strip()

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None

        if parsed.tzinfo is None:
            return None

        return parsed.astimezone(timezone.utc)

    def _filter_by_range(self, records, timestamp_key):
        """Support the documented S-AGRI range values: 1d, 7d, 30d."""

        range_value = request.args.get("range")

        if range_value not in ("1d", "7d", "30d"):
            return records

        days = int(range_value[:-1])
        threshold = datetime.now(timezone.utc) - timedelta(days=days)

        filtered = []

        for record in records:
            timestamp = self._parse_datetime(record.get(timestamp_key))

            if timestamp is not None and timestamp >= threshold:
                filtered.append(record)

        return filtered

    @staticmethod
    def _latest_or_404(records):
        if not records:
            return jsonify({"message": "No local data available."}), 404

        return jsonify(records[-1])

    # ========================================================
    # ROUTES
    # ========================================================

    def _register_routes(self):

        @self.app.get("/health")
        def health():
            return jsonify({
                "status": "OK",
                "service": "S-AGRI Local API",
                "node_id": self._config.node_id,
            })

        @self.app.get("/api/info")
        def info():
            return jsonify({
                "service": "S-AGRI Local API",
                "node_id": self._config.node_id,
                "sensor_file": str(self._config.sensor_output_file),
                "ai_results_file": str(self._config.ai_results_file),
                "camera_directory": str(self._config.camera_directory),
            })

        # ----------------------------------------------------
        # SENSOR ENDPOINTS
        # ----------------------------------------------------

        @self.app.get("/api/sensors/latest")
        def sensor_latest():
            records = self._projected_sensor_records()
            return self._latest_or_404(records)

        @self.app.get("/api/sensors/history")
        def sensor_history():
            limit = self._parse_limit()
            records = self._filter_by_range(
                self._projected_sensor_records(),
                "timestamp",
            )
            return jsonify(records[-limit:])

        # ----------------------------------------------------
        # WEATHER ENDPOINTS
        # ----------------------------------------------------

        @self.app.get("/api/weather/latest")
        def weather_latest():
            records = self._projected_weather_records()
            return self._latest_or_404(records)

        @self.app.get("/api/weather/history")
        def weather_history():
            limit = self._parse_limit()
            records = self._filter_by_range(
                self._projected_weather_records(),
                "timestamp",
            )
            return jsonify(records[-limit:])

        # ----------------------------------------------------
        # NODE STATUS ENDPOINT
        # ----------------------------------------------------

        @self.app.get("/api/nodes/status")
        def node_status():
            records = self._projected_status_records()
            return self._latest_or_404(records)

        # ----------------------------------------------------
        # AI ENDPOINTS
        # ----------------------------------------------------

        @self.app.get("/api/ai/latest")
        def ai_latest():
            records = self._projected_ai_records()
            return self._latest_or_404(records)

        @self.app.get("/api/ai-results")
        def ai_history():
            limit = self._parse_limit()
            records = self._filter_by_range(
                self._projected_ai_records(),
                "captured_at",
            )
            return jsonify(records[-limit:])

        # ----------------------------------------------------
        # LOCAL IMAGE ACCESS
        # ----------------------------------------------------

        @self.app.get("/api/images/<path:relative_path>")
        def get_image(relative_path):
            """
            Serve saved ESP32-CAM images to LAN clients.

            Example:
            /api/images/2026-08-17/esp_cam_01_xxx.jpg
            """

            return send_from_directory(
                self._config.camera_directory,
                relative_path,
            )

    # ========================================================
    # PROJECTED RECORD HELPERS
    # ========================================================

    def _projected_sensor_records(self):
        records = [
            self.projector.project_sensor(record)
            for record in self.sensor_store.read_all()
        ]

        return [r for r in records if self.projector.has_sensor_values(r)]

    def _projected_weather_records(self):
        records = [
            self.projector.project_weather(record)
            for record in self.sensor_store.read_all()
        ]

        return [r for r in records if self.projector.has_weather_values(r)]

    def _projected_status_records(self):
        records = [
            self.projector.project_status(record)
            for record in self.sensor_store.read_all()
        ]

        return [r for r in records if self.projector.has_status_values(r)]

    def _projected_ai_records(self):
        records = [
            self.projector.project_ai(record)
            for record in self.ai_store.read_all()
        ]

        return [
            r for r in records
            if r.get("captured_at") and r.get("image_path")
        ]

    # ========================================================
    # RUN SERVER
    # ========================================================

    def run(self, host: str = "0.0.0.0", port: int = 8000) -> None:
        self._config.ensure_directories()

        print("=" * 55)
        print("S-AGRI LOCAL API")
        print("=" * 55)
        print(f"Node ID : {self._config.node_id}")
        print(f"Host    : {host}")
        print(f"Port    : {port}")
        print()
        print(f"Health  : http://RASPBERRY_IP:{port}/health")
        print(f"Sensor  : http://RASPBERRY_IP:{port}/api/sensors/latest")
        print(f"AI      : http://RASPBERRY_IP:{port}/api/ai/latest")
        print("=" * 55)

        self.app.run(host=host, port=port, debug=False, threaded=True)
