class CloudShapeProjector:
    """
    Convert internal Raspberry Pi records into field names that match
    the S-AGRI API contract (see DATABASE_AND_SENSOR_API.pdf).

    This class only projects data — it does not send anything anywhere.
    sagri.local_api uses it to display cloud-shaped data locally;
    sagri.cloud.sync_worker uses the same projection as the payload it
    actually POSTs, so the two can't drift apart.
    """

    SENSOR_FIELD_ALIASES = {
        "soil_moisture": (
            "soil_moisture",
            "soil",
            "soil_moisture_percent",
        ),
        "vwc": (
            "vwc",
            "volumetric_water_content",
        ),
        "air_temp": (
            "air_temp",
            "temperature",
            "temp",
            "air_temperature",
        ),
        "air_humidity": (
            "air_humidity",
            "humidity",
            "relative_humidity",
        ),
        "co2": (
            "co2",
            "co2_ppm",
        ),
        "pressure": (
            "pressure",
            "pressure_hpa",
        ),
    }

    WEATHER_FIELD_ALIASES = {
        "solar_radiation": (
            "solar_radiation",
            "radiation",
        ),
        "wind_speed": (
            "wind_speed",
        ),
        "wind_direction": (
            "wind_direction",
        ),
        "rainfall": (
            "rainfall",
            "rain",
        ),
    }

    STATUS_FIELD_ALIASES = {
        "battery_pct": (
            "battery_pct",
            "battery",
        ),
        "solar_input_w": (
            "solar_input_w",
        ),
        "network_type": (
            "network_type",
        ),
        "uptime_sec": (
            "uptime_sec",
            "uptime",
        ),
    }

    def __init__(self, node_id):
        self.node_id = node_id

    @staticmethod
    def _first_present(source, aliases):
        for key in aliases:
            if key in source and source[key] is not None:
                return source[key]

        return None

    @staticmethod
    def _combine_packet_sources(packet):
        """
        Build a flat lookup view without modifying raw data.

        The serial receiver currently allows sensor values inside
        packet["data"]. Future firmware can also use more explicit
        nested dictionaries.
        """

        sources = [packet]

        for key in (
            "data",
            "sensor",
            "sensors",
            "weather",
            "status_data",
            "device_status",
        ):
            value = packet.get(key)

            if isinstance(value, dict):
                sources.append(value)

        combined = {}

        for source in sources:
            combined.update(source)

        return combined

    @staticmethod
    def _get_timestamp(record):
        """Prefer source timestamp, then use Raspberry Pi receive time."""

        for key in (
            "timestamp",
            "captured_at",
            "sensor_timestamp",
            "raspberry_timestamp",
            "raspi_received_time",
        ):
            value = record.get(key)

            if value:
                return value

        return None

    def _project_fields(self, packet, aliases):
        source = self._combine_packet_sources(packet)
        projected = {}

        for output_field, input_aliases in aliases.items():
            value = self._first_present(
                source,
                input_aliases,
            )

            if value is not None:
                projected[output_field] = value

        return projected

    def project_sensor(self, packet):
        result = {
            "node_id": self.node_id,
            "timestamp": self._get_timestamp(packet),
        }

        result.update(
            self._project_fields(
                packet,
                self.SENSOR_FIELD_ALIASES,
            )
        )

        return result

    def project_weather(self, packet):
        result = {
            "node_id": self.node_id,
            "timestamp": self._get_timestamp(packet),
        }

        result.update(
            self._project_fields(
                packet,
                self.WEATHER_FIELD_ALIASES,
            )
        )

        return result

    def project_status(self, packet):
        result = {
            "node_id": self.node_id,
            "timestamp": self._get_timestamp(packet),
        }

        result.update(
            self._project_fields(
                packet,
                self.STATUS_FIELD_ALIASES,
            )
        )

        return result

    def project_ai(self, record):
        return {
            "node_id": self.node_id,
            "captured_at": record.get("captured_at"),
            "image_path": record.get("image_path"),
            "label": record.get("label"),
            "confidence_score": record.get("confidence_score"),
            "model_version": record.get("model_version"),
        }

    @staticmethod
    def has_sensor_values(record):
        return any(
            key in record
            for key in (
                "soil_moisture",
                "vwc",
                "air_temp",
                "air_humidity",
                "co2",
                "pressure",
            )
        )

    @staticmethod
    def has_weather_values(record):
        return any(
            key in record
            for key in (
                "solar_radiation",
                "wind_speed",
                "wind_direction",
                "rainfall",
            )
        )

    @staticmethod
    def has_status_values(record):
        return any(
            key in record
            for key in (
                "battery_pct",
                "solar_input_w",
                "network_type",
                "uptime_sec",
            )
        )
