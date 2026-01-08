"""Math helpers."""


def safe_div(a, b, default=0.0):
    try:
        return a / b
    except Exception:
        return default
