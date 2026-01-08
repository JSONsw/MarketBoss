import os
from src.backtesting import trade_log


def test_log_and_read_trade(tmp_path):
    run_id = "testrun"
    path = tmp_path / f"trades-{run_id}.jsonl"
    trade = {"id": 1, "symbol": "ABC", "qty": 10}
    written = trade_log.log_trade(trade, run_id=run_id, path=str(path))
    assert os.path.exists(written)
    trades = list(trade_log.read_trades(str(path)))
    assert trades[0]["symbol"] == "ABC"
