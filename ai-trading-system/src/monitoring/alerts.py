"""Alerting utilities with webhook/email integrations.

This module writes durable alert logs and optionally forwards alerts
to a configured webhook and/or email using `config/alerts.yaml`.
"""

import os
from datetime import datetime, timezone
import json
import smtplib
import ssl
from time import sleep

try:
    import requests  # type: ignore
except Exception:
    requests = None

try:
    import yaml
except Exception:
    yaml = None


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


# Load alerts config (best-effort)
_alerts_config = {}
try:
    if yaml is not None:
        with open("config/alerts.yaml", "r", encoding="utf-8") as _f:
            _alerts_config = yaml.safe_load(_f) or {}
except Exception:
    _alerts_config = {}


def send_webhook(
    url: str, payload: dict, headers: dict = None, timeout: int = 5
) -> bool:
    """Send a JSON payload to `url`. Uses `requests` if available."""
    headers = headers or {"Content-Type": "application/json"}
    try:
        if requests is not None:
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
            return resp.status_code < 400
        # fallback to urllib
        from urllib import request as _request

        data = json.dumps(payload).encode("utf-8")
        req = _request.Request(url, data=data, headers=headers)
        with _request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.getcode() < 400
    except Exception:
        return False


def _send_with_retries(
    url: str,
    payload: dict,
    headers: dict = None,
    retries: int = 3,
    backoff_seconds: int = 1,
) -> bool:
    headers = headers or {}
    for attempt in range(1, retries + 1):
        ok = send_webhook(url, payload, headers=headers)
        if ok:
            return True
        sleep(backoff_seconds * attempt)
    return False


def send_email(
    smtp_server: str,
    port: int,
    username: str,
    password: str,
    to_addrs: str,
    subject: str,
    body: str,
) -> bool:
    """Send a simple plaintext email. Returns True on success."""
    try:
        lines = [
            f"From: {username}",
            f"To: {to_addrs}",
            f"Subject: {subject}",
            "",
            body,
        ]
        msg = "\r\n".join(lines)
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, port, timeout=10) as server:
            server.starttls(context=context)
            server.login(username, password)
            server.sendmail(username, [to_addrs], msg)
        return True
    except Exception:
        return False


def send_alert(message: str, level: str = "info", path: str = None) -> str:
    """Append an alert message to the alerts log and optionally forward it."""
    if path is None:
        path = os.path.join("logs", "alerts.log")
    _ensure_dir(os.path.dirname(path) or ".")
    ts = datetime.now(timezone.utc).isoformat()
    line = f"{ts} | {level.upper()} | {message}\n"
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except Exception:
            pass

    # attempt webhook notification if configured
    try:
        wh = _alerts_config.get("webhook", {})
        url = wh.get("url")
        if url:
            payload = {"timestamp": ts, "level": level, "message": message}
            headers = wh.get("headers") or {}
            retries = int(wh.get("retries", 3))
            backoff = int(wh.get("backoff_seconds", 1))
            _send_with_retries(
                url,
                payload,
                headers=headers,
                retries=retries,
                backoff_seconds=backoff,
            )
    except Exception:
        pass

    # attempt email notification if configured
    try:
        email_cfg = _alerts_config.get("email", {})
        if email_cfg and email_cfg.get("smtp_server"):
            send_email(
                email_cfg.get("smtp_server"),
                int(email_cfg.get("port", 587)),
                email_cfg.get("username"),
                email_cfg.get("password"),
                email_cfg.get("to_address"),
                f"[{level.upper()}] Alert from AI Trading",
                message,
            )
    except Exception:
        pass

    return path


__all__ = ["send_alert", "send_webhook", "send_email"]
