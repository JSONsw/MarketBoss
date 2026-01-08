# Requirements & Success Metrics

## Purpose
This document captures the high-level functional and non-functional requirements, success metrics, and acceptance criteria for the AI Trading System.

## Key Success Metrics (KPIs)
- **Annualized Return (net):** target > 10% (strategy-dependent)
- **Sharpe Ratio:** target > 1.2
- **Max Drawdown:** target < 15% (rolling, strategy-dependent)
- **Win Rate:** informational; target > 50% for many strategies
- **Profit Factor:** target > 1.5
- **Latency:** order round-trip < 500ms for live execution (broker dependent)

## Data Requirements
- **Sources:** market data (prices, volumes), reference data, fills/executions, corporate actions
- **Freshness:** intraday feeds < 1s delay for live execution; end-of-day for batch training
- **Retention:** at least 5 years of historical bars for backtesting unless specified otherwise
- **Validation:** schema checks, range checks, missing-value handling, duplicate detection

## Model Performance & Validation
- Use walk-forward cross-validation and out-of-sample testing
- Require performance consistency across market regimes (bull, bear, sideways)
- Monitor feature stability (population/stationarity drift)

## Backtest & Execution Fidelity
- Include realistic transaction costs and slippage modelling in backtests
- Reproduce live order execution behavior in simulated environment
- Maintain an immutable trade log for every backtest and live run

## Risk & Safety Gates
- Hard exposure limits per instrument and portfolio (`src/risk/exposure_limits.py`)
- Maximum position size and leverage controls
- Automatic stop-loss and time-based kill-switch for abnormal behavior

## Operational & QA Requirements
- Automated unit and integration test coverage for core modules (target > 80% for critical modules)
- CI pipeline to run tests and linting on PRs
- Monitoring + alerting on data pipeline failures, model performance degradation, and execution errors

## Acceptance Criteria for Releases
- All unit tests pass and CI green
- No new critical lint or type errors
- Deployment runbook updated and smoke tests passing in paper trading
- Manual sign-off after paper trading before live rollout

## Next Actionable Items (short-term)
1. Implement data validation and missing-value handling in `src/data_pipeline/`
2. Add immutable trade logging to `src/backtesting/trade_log.py` and `src/execution/order_executor.py`
3. Create walk-forward evaluation harness in `src/models/train_model.py`

---
Document created to capture agreed operational targets and acceptance gates. Update as priorities change.
