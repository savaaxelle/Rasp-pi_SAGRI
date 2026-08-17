from pathlib import Path

import serial
from serial import SerialException

BAUD_RATE = 115200
SERIAL_TIMEOUT = 2

# Allow the ESP32 to finish resetting after opening serial.
RESET_SETTLE_SECONDS = 2


class SerialLink:
    """
    Thin wrapper around a pyserial connection.

    The only class that talks to `serial.Serial` directly: port
    discovery, opening/closing, reading lines, and sending ACK/NACK.
    """

    def __init__(self, baud_rate: int = BAUD_RATE, timeout: int = SERIAL_TIMEOUT):
        self._baud_rate = baud_rate
        self._timeout = timeout
        self._connection = None

    @staticmethod
    def find_port() -> str:
        possible_ports = []

        possible_ports.extend(sorted(Path("/dev").glob("ttyUSB*")))
        possible_ports.extend(sorted(Path("/dev").glob("ttyACM*")))

        if not possible_ports:
            return None

        return str(possible_ports[0])

    @property
    def is_open(self) -> bool:
        return self._connection is not None and self._connection.is_open

    def open(self, port: str) -> None:
        self._connection = serial.Serial(
            port=port,
            baudrate=self._baud_rate,
            timeout=self._timeout,
        )

    def close(self) -> None:
        if self.is_open:
            self._connection.close()

    def read_line(self):
        """Read one line, returning None on empty/blank reads."""

        raw_data = self._connection.readline()

        if not raw_data:
            return None

        try:
            raw_line = raw_data.decode("utf-8").strip()
        except UnicodeDecodeError:
            raise ValueError("UTF8_ERROR")

        return raw_line or None

    def send_ack(self, sequence) -> None:
        message = f"ACK:{sequence}\n"

        self._connection.write(message.encode("utf-8"))
        self._connection.flush()

        print(f"[TX] ACK:{sequence}")

    def send_nack(self, sequence, reason: str) -> None:
        message = f"NACK:{sequence}:{reason}\n"

        self._connection.write(message.encode("utf-8"))
        self._connection.flush()

        print(f"[TX] NACK:{sequence}:{reason}")
