"""Time and schedule utilities."""


def now_iso():
    from datetime import datetime

    return datetime.utcnow().isoformat()
