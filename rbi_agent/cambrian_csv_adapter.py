#!/usr/bin/env python3
"""
Cambrian Data Adapter for Moon Dev RBI Agent
Converts Cambrian API data → CSV format that Moon Dev expects

Moon Dev expects CSV format:
datetime,open,high,low,close,volume
2023-01-01 00:00:00,16531.83,16532.69,16509.11,16510.82,231.05338022
"""

import os
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from rbi_agent.cambrian_fetcher import CambrianDataFetcher
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CambrianCSVAdapter:
    """
    Adapter to convert Cambrian API data → CSV format for Moon Dev RBI agent
    
    Moon Dev expects:
    - CSV files in: src/data/rbi/SYMBOL-TIMEFRAME.csv
    - Format: datetime,open,high,low,close,volume
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize adapter
        
        Args:
            output_dir: Directory to save CSV files (default: moon-dev-reference/src/data/rbi/)
        """
        self.cambrian_fetcher = CambrianDataFetcher()
        
        # Default to Moon Dev's expected location
        if output_dir is None:
            moon_dev_ref = Path(parent_dir) / "moon-dev-reference" / "src" / "data" / "rbi"
            self.output_dir = moon_dev_ref
        else:
            self.output_dir = Path(output_dir)
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ CSV adapter initialized, output dir: {self.output_dir}")
    
    def fetch_and_save_csv(
        self,
        symbol: str,
        days_back: int = 90,
        interval: str = "15m"
    ) -> Optional[str]:
        """
        Fetch data from Cambrian and save as CSV
        
        Args:
            symbol: Pacifica symbol (e.g., "SOL", "ETH", "BTC")
            days_back: Days of historical data
            interval: Candle interval ("15m", "1h", "4h", "1d")
            
        Returns:
            Path to saved CSV file, or None if failed
        """
        try:
            # Fetch data from Cambrian
            logger.info(f"Fetching {symbol} data from Cambrian ({days_back} days, {interval})...")
            
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days_back)
            
            after_time = int(start_time.timestamp())
            before_time = int(end_time.timestamp())
            
            # Get token address
            token_address = self.cambrian_fetcher.get_token_address(symbol)
            
            if not token_address:
                logger.warning(f"Token address not found for {symbol}, cannot fetch from Cambrian")
                return None
            
            # Fetch OHLCV
            df = self.cambrian_fetcher.fetch_ohlcv(
                token_address=token_address,
                after_time=after_time,
                before_time=before_time,
                interval=interval
            )
            
            if df is None or df.empty:
                logger.warning(f"No data returned for {symbol}")
                return None
            
            # Convert to Moon Dev format
            # Moon Dev expects: datetime,open,high,low,close,volume
            csv_df = pd.DataFrame({
                'datetime': df['timestamp'],
                'open': df['open'],
                'high': df['high'],
                'low': df['low'],
                'close': df['close'],
                'volume': df['volume']
            })
            
            # Sort by datetime (ascending)
            csv_df = csv_df.sort_values('datetime')
            
            # Save to CSV
            csv_filename = f"{symbol}-USD-{interval}.csv"
            csv_path = self.output_dir / csv_filename
            
            csv_df.to_csv(csv_path, index=False)
            logger.info(f"✅ Saved {len(csv_df)} candles to {csv_path}")
            
            return str(csv_path)
            
        except Exception as e:
            logger.error(f"Error fetching/saving {symbol} data: {e}", exc_info=True)
            return None
    
    def prepare_all_symbols(
        self,
        symbols: list = None,
        days_back: int = 90,
        interval: str = "15m"
    ) -> dict:
        """
        Prepare CSV files for multiple symbols
        
        Args:
            symbols: List of symbols (default: ["SOL", "ETH", "BTC"])
            days_back: Days of historical data
            interval: Candle interval
            
        Returns:
            Dict mapping symbol → CSV path (or None if failed)
        """
        if symbols is None:
            symbols = ["SOL", "ETH", "BTC"]
        
        results = {}
        
        for symbol in symbols:
            csv_path = self.fetch_and_save_csv(symbol, days_back, interval)
            results[symbol] = csv_path
        
        logger.info(f"✅ Prepared {len([v for v in results.values() if v])}/{len(symbols)} CSV files")
        return results


if __name__ == "__main__":
    # Test adapter
    adapter = CambrianCSVAdapter()
    
    # Prepare SOL, ETH, BTC data
    print("\n=== Preparing Cambrian Data for Moon Dev RBI Agent ===\n")
    
    results = adapter.prepare_all_symbols(
        symbols=["SOL", "ETH", "BTC"],
        days_back=90,
        interval="15m"
    )
    
    print("\n=== Results ===")
    for symbol, path in results.items():
        if path:
            print(f"✅ {symbol}: {path}")
        else:
            print(f"❌ {symbol}: Failed")

