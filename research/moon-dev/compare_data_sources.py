#!/usr/bin/env python3
"""
Data Accuracy Comparison: Pacifica vs Cambrian
Spot checks OHLCV data from both sources to verify alignment

Usage:
    python3 rbi_agent/compare_data_sources.py --symbol SOL --days 7
"""

import os
import sys
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional
import argparse

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from llm_agent.data.pacifica_fetcher import PacificaDataFetcher
from dotenv import load_dotenv

load_dotenv()

# Cambrian API configuration
CAMBRIAN_BASE_URL = "https://opabinia.cambrian.network/api/v1"  # Note: .network not .org
CAMBRIAN_API_KEY = os.getenv("CAMBRIAN_API_KEY")
if not CAMBRIAN_API_KEY:
    raise ValueError("CAMBRIAN_API_KEY environment variable not set")

# Token address mapping (partial)
TOKEN_ADDRESSES = {
    "SOL": "So11111111111111111111111111111111111111112",
    "ETH": "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",  # Wrapped ETH
    "BTC": "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E",  # Wrapped BTC
    "PUMP": None,  # Need to find
}


def fetch_cambrian_ohlcv(
    token_address: str,
    after_time: int,
    before_time: int,
    interval: str = "15m"
) -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV data from Cambrian API
    
    Args:
        token_address: Solana token address
        after_time: Unix timestamp (seconds)
        before_time: Unix timestamp (seconds)
        interval: 1m, 5m, 15m, 1h, 4h, 1d
        
    Returns:
        DataFrame with OHLCV data, or None if fetch fails
    """
    try:
        url = f"{CAMBRIAN_BASE_URL}/solana/ohlcv/token"
        params = {
            "token_address": token_address,
            "after_time": after_time,
            "before_time": before_time,
            "interval": interval
        }
        headers = {
            "X-API-Key": CAMBRIAN_API_KEY,  # Note: Capital X, capital K
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Cambrian API error: HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return None
        
        data = response.json()
        
        # Cambrian returns ClickHouse columnar format
        if not data or len(data) == 0:
            print("⚠️ No data returned from Cambrian")
            return None
        
        table = data[0]  # First table
        
        # Convert to DataFrame
        columns = [col["name"] for col in table.get("columns", [])]
        rows = table.get("data", [])
        
        if not rows:
            print("⚠️ Empty data array from Cambrian")
            return None
        
        df = pd.DataFrame(rows, columns=columns)
        
        # Standardize column names
        rename_map = {
            "openPrice": "open",
            "highPrice": "high",
            "lowPrice": "low",
            "closePrice": "close",
            "volume": "volume",
            "unixTime": "timestamp"
        }
        
        for old_name, new_name in rename_map.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        # Convert timestamp to datetime
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        
        # Sort by timestamp
        if "timestamp" in df.columns:
            df = df.sort_values("timestamp").reset_index(drop=True)
        
        return df
        
    except Exception as e:
        print(f"❌ Error fetching Cambrian data: {e}")
        return None


def fetch_pacifica_ohlcv(
    symbol: str,
    days_back: int,
    interval: str = "15m"
) -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV data from Pacifica API
    
    Args:
        symbol: Pacifica symbol (e.g., "SOL")
        days_back: Number of days to fetch
        interval: 15m, 1h, etc.
        
    Returns:
        DataFrame with OHLCV data, or None if fetch fails
    """
    try:
        fetcher = PacificaDataFetcher()
        
        # Calculate limit based on interval and days
        if interval == "15m":
            limit = days_back * 96  # 96 candles per day
        elif interval == "1h":
            limit = days_back * 24
        elif interval == "4h":
            limit = days_back * 6
        elif interval == "1d":
            limit = days_back
        else:
            limit = days_back * 96  # Default to 15m
        
        # Fetch kline data directly
        kline_df = fetcher.fetch_kline(
            symbol=symbol,
            interval=interval,
            limit=min(limit, 1000)  # Pacifica limit
        )
        
        return kline_df
        
    except Exception as e:
        print(f"❌ Error fetching Pacifica data: {e}")
        return None


def compare_data(
    symbol: str,
    days_back: int = 7,
    interval: str = "15m"
):
    """
    Compare OHLCV data from Pacifica and Cambrian
    
    Args:
        symbol: Token symbol (SOL, ETH, BTC)
        days_back: Number of days to compare
        interval: Candle interval
    """
    print("=" * 80)
    print(f"DATA ACCURACY COMPARISON: {symbol}")
    print("=" * 80)
    print(f"Period: Last {days_back} days")
    print(f"Interval: {interval}")
    print()
    
    # Get token address
    token_address = TOKEN_ADDRESSES.get(symbol)
    if not token_address:
        print(f"❌ No token address mapping for {symbol}")
        print(f"   Available mappings: {list(TOKEN_ADDRESSES.keys())}")
        return
    
    print(f"Token Address: {token_address}")
    print()
    
    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days_back)
    
    # Cambrian uses seconds
    cambrian_after = int(start_time.timestamp())
    cambrian_before = int(end_time.timestamp())
    
    print("Fetching data from Cambrian...")
    cambrian_df = fetch_cambrian_ohlcv(
        token_address=token_address,
        after_time=cambrian_after,
        before_time=cambrian_before,
        interval=interval
    )
    
    if cambrian_df is None or cambrian_df.empty:
        print("❌ Failed to fetch Cambrian data")
        return
    
    print(f"✅ Cambrian: {len(cambrian_df)} candles")
    print()
    
    print("Fetching data from Pacifica...")
    pacifica_df = fetch_pacifica_ohlcv(
        symbol=symbol,
        days_back=days_back,
        interval=interval
    )
    
    if pacifica_df is None or pacifica_df.empty:
        print("❌ Failed to fetch Pacifica data")
        return
    
    print(f"✅ Pacifica: {len(pacifica_df)} candles")
    print()
    
    # Compare data
    print("=" * 80)
    print("COMPARISON RESULTS")
    print("=" * 80)
    print()
    
    # Align timestamps for comparison
    # Cambrian: timestamp column (datetime)
    # Pacifica: timestamp column (datetime)
    
    if "timestamp" not in cambrian_df.columns or "timestamp" not in pacifica_df.columns:
        print("❌ Missing timestamp columns")
        print(f"   Cambrian columns: {cambrian_df.columns.tolist()}")
        print(f"   Pacifica columns: {pacifica_df.columns.tolist()}")
        return
    
    # Find overlapping time range
    cambrian_start = cambrian_df["timestamp"].min()
    cambrian_end = cambrian_df["timestamp"].max()
    pacifica_start_dt = pacifica_df["timestamp"].min()
    pacifica_end_dt = pacifica_df["timestamp"].max()
    
    print(f"Time Ranges:")
    print(f"  Cambrian: {cambrian_start} to {cambrian_end}")
    print(f"  Pacifica: {pacifica_start_dt} to {pacifica_end_dt}")
    print()
    
    # Find overlapping candles (within 1 minute tolerance)
    comparisons = []
    
    for _, pac_row in pacifica_df.iterrows():
        pac_time = pac_row["timestamp"]
        
        # Find closest Cambrian candle (within 1 minute)
        time_diffs = (cambrian_df["timestamp"] - pac_time).abs()
        closest_idx = time_diffs.idxmin()
        
        if time_diffs[closest_idx] <= timedelta(minutes=1):
            cam_row = cambrian_df.loc[closest_idx]
            
            comparisons.append({
                "timestamp": pac_time,
                "pacifica_close": pac_row.get("close", None),
                "cambrian_close": cam_row.get("close", None),
                "pacifica_volume": pac_row.get("volume", None),
                "cambrian_volume": cam_row.get("volume", None),
            })
    
    if not comparisons:
        print("⚠️ No overlapping candles found")
        print("   (Time ranges may not overlap or tolerance too strict)")
        return
    
    print(f"Found {len(comparisons)} overlapping candles")
    print()
    
    # Calculate differences
    price_diffs = []
    volume_diffs = []
    
    for comp in comparisons:
        if comp["pacifica_close"] and comp["cambrian_close"]:
            price_diff_pct = abs(comp["pacifica_close"] - comp["cambrian_close"]) / comp["pacifica_close"] * 100
            price_diffs.append(price_diff_pct)
        
        if comp["pacifica_volume"] and comp["cambrian_volume"]:
            vol_diff_pct = abs(comp["pacifica_volume"] - comp["cambrian_volume"]) / comp["pacifica_volume"] * 100 if comp["pacifica_volume"] > 0 else 0
            volume_diffs.append(vol_diff_pct)
    
    # Statistics
    print("Price Comparison (Close Price):")
    if price_diffs:
        avg_diff = sum(price_diffs) / len(price_diffs)
        max_diff = max(price_diffs)
        min_diff = min(price_diffs)
        
        print(f"  Average Difference: {avg_diff:.4f}%")
        print(f"  Max Difference: {max_diff:.4f}%")
        print(f"  Min Difference: {min_diff:.4f}%")
        
        if avg_diff < 0.1:
            print("  ✅ EXCELLENT - Prices align closely (<0.1% avg)")
        elif avg_diff < 0.5:
            print("  ✅ GOOD - Prices align well (<0.5% avg)")
        elif avg_diff < 1.0:
            print("  ⚠️ ACCEPTABLE - Some variance (<1% avg)")
        else:
            print("  ❌ POOR - Significant variance (>1% avg)")
    else:
        print("  ⚠️ No price data to compare")
    
    print()
    
    print("Volume Comparison:")
    if volume_diffs:
        avg_diff = sum(volume_diffs) / len(volume_diffs)
        max_diff = max(volume_diffs)
        
        print(f"  Average Difference: {avg_diff:.2f}%")
        print(f"  Max Difference: {max_diff:.2f}%")
        
        if avg_diff < 10:
            print("  ✅ GOOD - Volumes align reasonably (<10% avg)")
        elif avg_diff < 25:
            print("  ⚠️ ACCEPTABLE - Some variance (<25% avg)")
        else:
            print("  ❌ POOR - Significant variance (>25% avg)")
            print("     (Expected: Cambrian is multi-venue, Pacifica is single venue)")
    else:
        print("  ⚠️ No volume data to compare")
    
    print()
    
    # Sample comparisons
    print("Sample Comparisons (Last 5 candles):")
    print("-" * 80)
    print(f"{'Timestamp':<20} {'Pacifica Close':<15} {'Cambrian Close':<15} {'Price Diff %':<12}")
    print("-" * 80)
    
    for comp in comparisons[-5:]:
        timestamp_str = comp["timestamp"].strftime("%Y-%m-%d %H:%M")
        pac_close = comp["pacifica_close"] if comp["pacifica_close"] else "N/A"
        cam_close = comp["cambrian_close"] if comp["cambrian_close"] else "N/A"
        
        if pac_close != "N/A" and cam_close != "N/A":
            diff_pct = abs(pac_close - cam_close) / pac_close * 100
            print(f"{timestamp_str:<20} ${pac_close:<14.4f} ${cam_close:<14.4f} {diff_pct:<11.4f}%")
        else:
            print(f"{timestamp_str:<20} {pac_close:<15} {cam_close:<15} N/A")
    
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Compare Pacifica vs Cambrian data accuracy")
    parser.add_argument("--symbol", type=str, default="SOL", help="Symbol to compare (SOL, ETH, BTC)")
    parser.add_argument("--days", type=int, default=7, help="Days of data to compare")
    parser.add_argument("--interval", type=str, default="15m", help="Candle interval")
    
    args = parser.parse_args()
    
    compare_data(
        symbol=args.symbol,
        days_back=args.days,
        interval=args.interval
    )


if __name__ == "__main__":
    main()

