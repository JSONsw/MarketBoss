"""Order execution logic.

Executes orders through broker APIs and logs all trades to immutable
JSONL logs for compliance and analysis.
"""

from typing import Dict, Optional
from datetime import datetime, timezone

from .broker_api import place_order
from src.backtesting.trade_log import log_trade
from src.monitoring.structured_logger import get_logger
from src.risk.exposure_limits import check_exposure

logger = get_logger()


def execute_order(
    order: Dict,
    run_id: Optional[str] = None,
    log_path: Optional[str] = None,
    check_exposure_limits: bool = True,
    portfolio: Optional[Dict] = None,
) -> Dict:
    """
    Execute an order through the broker and log the trade.

    :param order: Order dict with symbol, qty, price, side, etc.
    :param run_id: Run identifier for trade log grouping
    :param log_path: Custom path for trade log
    :param check_exposure_limits: Whether to validate exposure before execution
    :param portfolio: Current portfolio state for exposure checks
    :return: Execution result dict with status, filled_qty, executed_price, etc.
    """
    try:
        # Validate exposure limits if requested
        if check_exposure_limits and portfolio:
            ok, violations = check_exposure(portfolio)
            if not ok:
                logger.error("order_rejected_exposure_limits", order=order, violations=violations)
                return {
                    "status": "rejected",
                    "reason": "Exposure limits exceeded",
                    "violations": violations,
                }
        
        # Place the order through broker
        execution_result = place_order(order)
        
        # Build trade record for logging
        trade_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": order.get("symbol"),
            "side": order.get("side", "buy"),
            "qty": order.get("qty"),
            "limit_price": order.get("price"),
            "filled_qty": execution_result.get("filled_qty", 0),
            "executed_price": execution_result.get("executed_price", order.get("price")),
            "status": execution_result.get("status", "unknown"),
            "order_id": execution_result.get("order_id"),
            "notional": execution_result.get("notional", 0),
            "commission": execution_result.get("commission", 0),
            "slippage": execution_result.get("slippage", 0),
        }
        
        # Log the trade immutably
        log_trade(trade_record, run_id=run_id, path=log_path)
        logger.info(
            "order_executed",
            symbol=trade_record["symbol"],
            side=trade_record["side"],
            filled_qty=trade_record["filled_qty"],
            executed_price=trade_record["executed_price"],
            status=trade_record["status"],
        )
        
        return execution_result
        
    except Exception as e:
        logger.error("order_execution_error", order=order, error=str(e))
        return {
            "status": "error",
            "reason": str(e),
        }


__all__ = ["execute_order"]
