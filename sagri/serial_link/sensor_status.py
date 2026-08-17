class SensorStatusValidator:
    """Validates the optional 'status' block inside a sensor packet."""

    @staticmethod
    def all_sensors_ok(packet: dict) -> bool:
        status = packet.get("status")

        # Older ESP32 firmware may not send sensor status.
        if status is None:
            print("[INFO] Packet does not contain a 'status' field.")
            return True

        if not isinstance(status, dict):
            print("[WARNING] Invalid sensor status format.")
            return False

        all_ok = True

        for sensor_name, sensor_status in status.items():
            if isinstance(sensor_status, dict):
                sensor_ok = sensor_status.get("ok", True)
                error_message = sensor_status.get("error", "UNKNOWN_ERROR")
            elif isinstance(sensor_status, bool):
                sensor_ok = sensor_status
                error_message = "UNKNOWN_ERROR"
            else:
                print(f"[WARNING] Invalid status for {sensor_name}.")
                all_ok = False
                continue

            if sensor_ok:
                print(f"[SENSOR OK] {sensor_name}")
            else:
                all_ok = False
                print(f"[SENSOR ERROR] {sensor_name}: {error_message}")

        return all_ok
