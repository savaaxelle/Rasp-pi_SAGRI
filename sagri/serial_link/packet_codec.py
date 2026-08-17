import json


class Crc16Ccitt:
    """
    CRC-16/CCITT-FALSE checksum calculator.

    Polynomial : 0x1021
    Initial    : 0xFFFF
    """

    @staticmethod
    def compute(data: bytes) -> int:
        crc = 0xFFFF

        for byte in data:
            crc ^= byte << 8

            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ 0x1021) & 0xFFFF
                else:
                    crc = (crc << 1) & 0xFFFF

        return crc


class SensorPacketCodec:
    """
    Parses and validates 'JSON*CRC' lines sent by the ESP32 over serial.

    Example:
    {"seq":1,"data":{"temperature":28.5}}*A12B

    Pure and I/O-free, so it can be unit tested without a serial port.
    """

    def __init__(self, crc_calculator: Crc16Ccitt = None):
        self._crc_calculator = crc_calculator or Crc16Ccitt()

    def decode(self, raw_line: str) -> dict:
        if "*" not in raw_line:
            raise ValueError("CRC_SEPARATOR_NOT_FOUND")

        json_text, received_crc_text = raw_line.rsplit("*", 1)

        received_crc_text = received_crc_text.strip().upper()

        try:
            received_crc = int(received_crc_text, 16)
        except ValueError:
            raise ValueError("INVALID_CRC_FORMAT")

        calculated_crc = self._crc_calculator.compute(json_text.encode("utf-8"))

        if calculated_crc != received_crc:
            raise ValueError(
                f"CRC_MISMATCH:{received_crc:04X}:{calculated_crc:04X}"
            )

        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            raise ValueError("INVALID_JSON")
