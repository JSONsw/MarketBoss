import os
from src.monitoring import alerts, dashboard


def test_send_alert_writes_log(tmp_path):
    p = tmp_path / "alerts.log"
    path = alerts.send_alert("test message", level="warning", path=str(p))
    assert os.path.exists(path)
    txt = open(path, "r", encoding="utf-8").read()
    assert "WARNING" in txt or "WARNING" in txt.upper()


def test_dashboard_increment_and_gauge(tmp_path):
    mpath = str(tmp_path / "metrics.json")
    p1 = dashboard.increment("ingested_records", value=3, path=mpath)
    assert os.path.exists(p1)
    p2 = dashboard.set_gauge("last_run_duration_s", 2.5, path=mpath)
    data = open(p2, "r", encoding="utf-8").read()
    assert "ingested_records" in data and "last_run_duration_s" in data
