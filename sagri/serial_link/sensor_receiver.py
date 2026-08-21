import sys
import time

from serial import SerialException

from sagri.config import ProjectConfig
from sagri.serial_link.duplicate_filter import DuplicatePacketFilter
from sagri.serial_link.packet_codec import SensorPacketCodec
from sagri.serial_link.sensor_status import SensorStatusValidator
from sagri.serial_link.serial_transport import SerialLink
from sagri.storage.sensor_repository import SensorDataRepository
from sagri.time_utils import utc_now_iso


class SerialSensorReceiver:
    """
    Orchestrates the ESP32 serial link: find port -> read packets ->
    validate -> store -> ACK/NACK.

    Every actual capability (transport, codec, storage, sensor-status
    rules, dedup) is injected, so this class only sequences calls.
    """

    def __init__(
        self,
        config: ProjectConfig,
        repository: SensorDataRepository,
        codec: SensorPacketCodec,
        link: SerialLink,
        status_validator: SensorStatusValidator,
        dup_filter: DuplicatePacketFilter,
    ):
        self._config = config
        self._repository = repository
        self._codec = codec
        self._link = link
        self._status_validator = status_validator
        self._dup_filter = dup_filter

    def run(self) -> None:
        self._config.ensure_directories()

        print("=" * 50)
        print("ESP32 JSON SERIAL RECEIVER + CRC + ACK")
        print("=" * 50)
        print(f"Project directory : {self._config.project_directory}")
        print(f"Storage root      : {self._config.storage_root}")
        print(f"Output file       : {self._config.sensor_output_file}")
        print()

        port = self._link.find_port()

        if port is None:
            print("ERROR: ESP32 serial port was not found.")
            print("Check the USB cable and ESP32 connection.")
            print()
            print("Check available serial ports with:")
            print("ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null")
            sys.exit(1)

        print(f"[OK] ESP32 detected on: {port}")

        try:
            self._link.open(port)
        except SerialException as error:
            print(f"[SERIAL ERROR] {error}")
            sys.exit(1)

        # Allow the ESP32 to finish resetting after opening serial.
        time.sleep(2)

        print()
        print("[OK] Serial connection established.")
        print("[WAIT] Waiting for ESP32 data...")
        print()

        try:
            self._receive_loop()
        except KeyboardInterrupt:
            print()
            print("[STOP] Receiver stopped by user.")
        finally:
            self._link.close()
            print("[OK] Serial connection closed.")

    def _receive_loop(self) -> None:
        while True:
            try:
                raw_line = self._link.read_line()
            except SerialException as error:
                print(f"[SERIAL ERROR] {error}")
                break
            except ValueError:
                print("[ERROR] Received serial data is not valid UTF-8.")
                continue

            if raw_line is None:
                continue

            if not self._codec.is_data_packet(raw_line):
                # The firmware also prints plain debug/status text
                # (sensor dumps, retry logs) — echo it like a serial
                # monitor, but there's nothing to ACK/NACK.
                print(f"[ESP32] {raw_line}")
                continue

            print()
            print(f"[RX] {raw_line}")

            try:
                sequence, packet = self._codec.decode(raw_line)
            except ValueError as error:
                # No trustworthy sequence to reply to — the firmware
                # will retry and time out on its own.
                print(f"[PACKET ERROR] {error}")
                continue

            print(f"[CRC OK] Packet #{sequence}")

            if self._dup_filter.is_duplicate(sequence):
                print(f"[DUPLICATE] Packet #{sequence} has already been received.")
                self._link.send_ack(sequence)
                continue

            sensors_ok = self._status_validator.all_sensors_ok(packet)
            packet["receiver_status"] = "OK" if sensors_ok else "SENSOR_ERROR"
            packet["raspberry_timestamp"] = utc_now_iso()

            try:
                saved_path = self._repository.save(packet)
            except Exception as error:
                print(f"[SAVE ERROR] {error}")
                self._link.send_nack(sequence)
                continue

            self._dup_filter.remember(sequence)

            print(f"[SAVED] Packet #{sequence} -> {saved_path}")

            self._link.send_ack(sequence)
