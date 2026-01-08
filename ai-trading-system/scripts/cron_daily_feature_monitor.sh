#!/usr/bin/env bash
# Cron wrapper to run daily feature monitor.
# Example crontab entry (runs daily at 06:00):
# 0 6 * * * /path/to/ai-trading-system/scripts/cron_daily_feature_monitor.sh >> /var/log/feature_monitor.log 2>&1

set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# Activate virtualenv if desired (uncomment and adjust)
# source /path/to/venv/bin/activate

python scripts/daily_feature_monitor.py
