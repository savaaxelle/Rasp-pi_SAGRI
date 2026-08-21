import serial
from serial import SerialException
from serial.tools import list_ports

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
        """
        Find a connected serial device.

        Uses pyserial's own device scanner instead of matching
        Linux-only /dev/ttyUSB*/ttyACM* names, so this works the same
        way on the Pi (Linux) and on a dev machine (Windows COMx,
        macOS /dev/cu.*) for local testing/debugging.
        """

        ports = list(list_ports.comports())

        if not ports:
            return None

        return ports[0].device

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
        # "ACK|<seq>" — the ESP32 firmware compares this exact string
        # (waitForUsbAck() in All_in_one_belumtestrum.ino), so the
        # format must match precisely: pipe-separated, no extra text.
        message = f"ACK|{sequence}\n"

        self._connection.write(message.encode("utf-8"))
        self._connection.flush()

        print(f"[TX] ACK|{sequence}")

    def send_nack(self, sequence) -> None:
        message = f"NACK|{sequence}\n"

        self._connection.write(message.encode("utf-8"))
        self._connection.flush()

        print(f"[TX] NACK|{sequence}")
