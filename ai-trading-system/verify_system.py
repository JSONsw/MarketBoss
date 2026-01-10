#!/usr/bin/env python
"""Quick verification that all MarketBoss components are ready for paper trading."""

import sys
from pathlib import Path

def check_file(path: str, description: str) -> bool:
    p = Path(path)
    if p.exists():
        size = p.stat().st_size
        print(f"✓ {description:<40} {p.name:<30} ({size:>8,} bytes)")
        return True
    else:
        print(f"✗ {description:<40} MISSING")
        return False

def check_import(module: str, description: str) -> bool:
    try:
        __import__(module)
        print(f"✓ {description:<40} {module}")
        return True
    except ImportError as e:
        print(f"✗ {description:<40} {module} (ImportError: {str(e)[:40]}...)")
        return False

def main():
    print("\n" + "="*100)
    print("MarketBoss Platform - Pre-Launch Verification")
    print("="*100 + "\n")
    
    checks = []
    
    # Data files
    print("DATA FILES:")
    checks.append(check_file("data/market_data.jsonl", "Market data (OHLCV bars)"))
    checks.append(check_file("data/signals.jsonl", "Trading signals"))
    print()
    
    # Scripts
    print("EXECUTABLE SCRIPTS:")
    checks.append(check_file("dashboard/app.py", "Streamlit dashboard"))
    checks.append(check_file("scripts/run_paper_trading.py", "Paper trading executor"))
    checks.append(check_file("scripts/run_training.py", "Training runner"))
    checks.append(check_file("scripts/run_backtest.py", "Backtest runner"))
    print()
    
    # Models
    print("MODEL CHECKPOINTS:")
    model_files = list(Path("models").glob("model_*.pkl"))
    if model_files:
        for model_file in sorted(model_files)[-3:]:
            meta_file = model_file.with_suffix(".pkl_metadata.json")
            if meta_file.exists():
                print(f"✓ {'Latest trained model':<40} {model_file.name}")
            else:
                print(f"⚠ {'Model without metadata':<40} {model_file.name}")
        checks.append(True)
    else:
        print(f"✗ {'Trained models':<40} NO MODELS FOUND")
        checks.append(False)
    print()
    
    # Python packages
    print("PYTHON DEPENDENCIES:")
    checks.append(check_import("streamlit", "Streamlit (dashboard)"))
    checks.append(check_import("pandas", "Pandas (data manipulation)"))
    checks.append(check_import("numpy", "NumPy (numerics)"))
    checks.append(check_import("xgboost", "XGBoost (ML model)"))
    alpaca_ok = check_import("alpaca_trade_api", "Alpaca Trade API (paper trading)")
    if not alpaca_ok:
        print("  → Install with: pip install alpaca-trade-api")
    checks.append(alpaca_ok)
    print()
    
    # Documentation
    print("DOCUMENTATION:")
    checks.append(check_file("DASHBOARD_GUIDE.md", "Dashboard user guide"))
    checks.append(check_file("IMPLEMENTATION_STATUS.md", "Implementation status"))
    checks.append(check_file("PROGRESS.md", "Project progress log"))
    print()
    
    # Summary
    total = len(checks)
    passed = sum(checks)
    
    print("="*100)
    print(f"SUMMARY: {passed}/{total} checks passed")
    print("="*100)
    
    if passed == total:
        print("\n✓ ALL SYSTEMS GO! Ready to launch dashboard and paper trading.\n")
        print("NEXT STEPS:")
        print("  1. Configure Alpaca API credentials (if running paper trading):")
        print("     export APCA_API_KEY_ID='your_key'")
        print("     export APCA_API_SECRET_KEY='your_secret'")
        print("     export APCA_API_BASE_URL='https://paper-api.alpaca.markets'")
        print()
        print("  2. Launch dashboard:")
        print("     streamlit run dashboard/app.py")
        print()
        print("  3. Start paper trading:")
        print("     python scripts/run_paper_trading.py --signals data/signals.jsonl --max-trades 50")
        print()
        return 0
    else:
        print(f"\n⚠ {total - passed} checks failed. Review items marked with ✗ above.\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
