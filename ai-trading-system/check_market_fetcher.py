#!/usr/bin/env python
"""Check if the live market fetcher can operate."""

import os
from dotenv import load_dotenv

load_dotenv()

apca_key = os.getenv("APCA_API_KEY_ID")
apca_secret = os.getenv("APCA_API_SECRET_KEY")

print("=" * 60)
print("Live Market Fetcher Operational Status")
print("=" * 60)

print("\nAlpaca API Configuration:")
print(f"  APCA_API_KEY_ID:    {'SET' if apca_key else 'NOT SET'}")
print(f"  APCA_API_SECRET_KEY: {'SET' if apca_secret else 'NOT SET'}")

if apca_key and apca_secret:
    print("\n✓ All credentials present")
    
    from src.data_pipeline.market_fetcher import MarketFetcher
    try:
        fetcher = MarketFetcher()
        print("✓ MarketFetcher instantiated successfully")
        print(f"✓ Connected to: {fetcher.base_url}")
        print("\n✅ LIVE MARKET FETCHER IS OPERATIONAL")
        
    except Exception as e:
        print(f"✗ Error initializing MarketFetcher: {e}")
        print("\n❌ LIVE MARKET FETCHER CANNOT OPERATE")
else:
    print("\n✗ Missing credentials")
    if not apca_key:
        print("  - APCA_API_KEY_ID is not set")
    if not apca_secret:
        print("  - APCA_API_SECRET_KEY is not set")
    print("\n❌ LIVE MARKET FETCHER CANNOT OPERATE")
    print("\nTo enable live market fetcher:")
    print("  1. Get Alpaca API credentials from https://alpaca.markets")
    print("  2. Add to .env file:")
    print("     APCA_API_KEY_ID=your_key")
    print("     APCA_API_SECRET_KEY=your_secret")

print("=" * 60)
