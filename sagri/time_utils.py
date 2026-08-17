from datetime import datetime, timezone


def utc_now_iso() -> str:
    """Return current UTC time in ISO 8601 format ending in Z."""

    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
