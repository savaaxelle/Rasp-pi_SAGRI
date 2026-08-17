import requests

USER_AGENT = "S-AGRI-Sensor/1.0"

SENSOR_DATA_PATH = "/sensors/data"
WEATHER_READINGS_PATH = "/weather-readings"
NODE_STATUS_PATH = "/nodes/status"
AI_RESULT_PATH = "/ai/result"

REQUEST_TIMEOUT_SECONDS = 10


class SagriCloudClient:
    """
    Thin HTTP client for the S-AGRI cloud contract
    (see DATABASE_AND_SENSOR_API.pdf).

    The site sits behind Cloudflare, which blocks requests with a
    default/missing User-Agent (403 "error 1010") — every request here
    always sets a custom one. One method per endpoint; each POSTs a
    single row, matching the documented "no batch" contract.
    """

    def __init__(self, base_url: str, timeout: float = REQUEST_TIMEOUT_SECONDS):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        })

    def _post(self, path: str, payload: dict):
        """
        POST one row. Returns (success, status_code, body).

        success is True only on HTTP 201 (documented success code).
        body is the parsed JSON response, or None if it wasn't JSON.
        """

        url = self._base_url + path

        try:
            response = self._session.post(
                url,
                json=payload,
                timeout=self._timeout,
            )
        except requests.RequestException as error:
            return False, None, {"message": str(error)}

        try:
            body = response.json()
        except ValueError:
            body = None

        return response.status_code == 201, response.status_code, body

    def post_sensor_reading(self, payload: dict):
        return self._post(SENSOR_DATA_PATH, payload)

    def post_weather_reading(self, payload: dict):
        return self._post(WEATHER_READINGS_PATH, payload)

    def post_node_status(self, payload: dict):
        return self._post(NODE_STATUS_PATH, payload)

    def post_ai_result(self, payload: dict):
        return self._post(AI_RESULT_PATH, payload)
