import json

# Every DATA packet from the ESP32 sensor node starts with this prefix.
# Everything else on the line (sensor-reading printouts, retry/status
# logs) is plain debug text, not a packet.
DATA_PACKET_PREFIX = "DATA|"


class Crc16Modbus:
    """
    CRC-16/MODBUS checksum calculator.

    Matches calculateCRC16Modbus() in the ESP32 sensor firmware
    (All_in_one_belumtestrum.ino): reflected poly 0xA001, init 0xFFFF.
    """

    @staticmethod
    def compute(data: bytes) -> int:
        crc = 0xFFFF

        for byte in data:
            crc ^= byte

            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1

        return crc


class SensorPacketCodec:
    """
    Parses and validates 'DATA|<sequence>|<CRC>|<JSON>' lines sent by
    the ESP32 sensor node over USB serial.

    Example:
    DATA|20|10D2|{"id":"nodeSensor","soilMoisture":0, ...}

    The CRC covers "<sequence>|<JSON>" (matching the firmware's
    sendUsbWithAck()), using CRC-16/MODBUS. Pure and I/O-free, so it
    can be unit tested without a serial port.
    """

    def __init__(self, crc_calculator: Crc16Modbus = None):
        self._crc_calculator = crc_calculator or Crc16Modbus()

    @staticmethod
    def is_data_packet(raw_line: str) -> bool:
        """
        Whether a line is a DATA|... packet, as opposed to the
        firmware's other Serial.println() debug/status text (sensor
        dumps, retry logs, etc.), which should just be echoed, not
        parsed or ACKed.
        """

        return raw_line.startswith(DATA_PACKET_PREFIX)

    def decode(self, raw_line: str):
        """Returns (sequence: int, packet: dict). Raises ValueError."""

        parts = raw_line.split("|", 3)

        if len(parts) != 4 or parts[0] != "DATA":
            raise ValueError("MALFORMED_PACKET")

        _prefix, seq_text, crc_text, json_text = parts

        try:
            sequence = int(seq_text)
        except ValueError:
            raise ValueError("INVALID_SEQUENCE")

        try:
            received_crc = int(crc_text, 16)
        except ValueError:
            raise ValueError("INVALID_CRC_FORMAT")

        crc_input = f"{seq_text}|{json_text}".encode("utf-8")
        calculated_crc = self._crc_calculator.compute(crc_input)

        if calculated_crc != received_crc:
            raise ValueError(
                f"CRC_MISMATCH:{received_crc:04X}:{calculated_crc:04X}"
            )

        try:
            packet = json.loads(json_text)
        except json.JSONDecodeError:
            raise ValueError("INVALID_JSON")

        return sequence, packet
