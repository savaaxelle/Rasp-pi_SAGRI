import json
from datetime import datetime
from pathlib import Path

DATE_FORMAT = "%Y-%m-%d"


class CaptureSchedule:
    """
    Decides whether a scheduled capture is due right now, and
    remembers the last date each scheduled hour already fired.

    Mirrors the old ESP32 firmware's NVS-backed lastCaptureDateXX
    bookkeeping (see esp32_cam's performScheduledCapture()), except
    this now lives on the Pi — so the schedule itself (which hours) is
    just Pi-side config, changeable without ever touching firmware.
    """

    def __init__(self, state_file: Path, hours: tuple):
        self._state_file = state_file
        self._hours = hours
        self._last_captured = self._load()

    def _load(self) -> dict:
        if not self._state_file.exists():
            return {}

        try:
            with self._state_file.open(mode="r", encoding="utf-8") as file:
                data = json.load(file)
        except (json.JSONDecodeError, OSError):
            return {}

        return data if isinstance(data, dict) else {}

    def _save(self) -> None:
        self._state_file.parent.mkdir(parents=True, exist_ok=True)

        with self._state_file.open(mode="w", encoding="utf-8") as file:
            json.dump(self._last_captured, file, ensure_ascii=False, indent=2)

    def due_hour(self, now: datetime):
        """
        Return the scheduled hour that's due right now, or None.

        "Due" means: the current hour is one of the scheduled hours,
        and today's capture for that hour hasn't happened yet. This
        stays true for the whole hour (not just at minute 0), so a
        restart mid-hour still catches a capture it would otherwise
        have missed.
        """

        if now.hour not in self._hours:
            return None

        key = str(now.hour)
        today = now.strftime(DATE_FORMAT)

        if self._last_captured.get(key) == today:
            return None

        return now.hour

    def mark_captured(self, hour: int, now: datetime) -> None:
        self._last_captured[str(hour)] = now.strftime(DATE_FORMAT)
        self._save()
