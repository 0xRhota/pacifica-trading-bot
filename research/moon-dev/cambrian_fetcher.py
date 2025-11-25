"""
Cambrian Data Fetcher for RBI Agent
Fetches historical OHLCV data from Cambrian API for backtesting

Usage:
    fetcher = CambrianDataFetcher()
    df = fetcher.fetch_ohlcv(
        token_address="So11111111111111111111111111111111111111112",
        after_time=1735689600,
        before_time=1735776000,
        interval="15m"
    )
"""

import requests
import logging
import pandas as pd
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class CambrianDataFetcher:
    """Fetch historical OHLCV data from Cambrian API"""
    
    BASE_URL = "https://opabinia.cambrian.network/api/v1"
    
    # Token address mapping (Pacifica symbol → Solana token address)
    TOKEN_ADDRESSES = {
        "SOL": "So11111111111111111111111111111111111111112",  # Wrapped SOL
        "ETH": "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",  # Wrapped ETH
        "BTC": "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E",  # Wrapped BTC
        # Note: PUMP and other tokens need addresses - will lookup dynamically
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Cambrian data fetcher
        
        Args:
            api_key: Cambrian API key (defaults to env var)
        """
        self.api_key = api_key or os.getenv("CAMBRIAN_API_KEY", "doug.ZbEScx8M4zlf7kDn")
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def get_token_address(self, symbol: str) -> Optional[str]:
        """
        Get Solana token address for a Pacifica symbol
        
        Args:
            symbol: Pacifica symbol (e.g., "SOL", "ETH", "BTC")
            
        Returns:
            Solana token address or None if not found
        """
        # Check cache first
        if symbol in self.TOKEN_ADDRESSES:
            return self.TOKEN_ADDRESSES[symbol]
        
        # Try to lookup via Cambrian token details endpoint
        # For now, return None - will need to handle unmapped symbols
        logger.warning(f"Token address not found for {symbol} - may need manual mapping")
        return None
    
    def fetch_ohlcv(
        self,
        token_address: str,
        after_time: int,
        before_time: int,
        interval: str = "15m"
    ) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data from Cambrian API
        
        Args:
            token_address: Solana token address (base58)
            after_time: Unix timestamp (seconds) - start time
            before_time: Unix timestamp (seconds) - end time
            interval: Candle interval (1m, 5m, 15m, 1h, 4h, 1d)
            
        Returns:
            DataFrame with OHLCV data, or None if fetch fails
        """
        try:
            url = f"{self.BASE_URL}/solana/ohlcv/token"
            params = {
                "token_address": token_address,
                "after_time": after_time,
                "before_time": before_time,
                "interval": interval
            }
            
            response = requests.get(url, params=params, headers=self.headers, timeout=60)
            
            if response.status_code != 200:
                logger.error(f"Cambrian API error: HTTP {response.status_code}")
                logger.error(f"Response: {response.text[:200]}")
                return None
            
            data = response.json()
            
            # Cambrian returns ClickHouse columnar format
            if not data or len(data) == 0:
                logger.warning("No data returned from Cambrian")
                return None
            
            table = data[0]  # First table
            
            # Convert to DataFrame
            columns = [col["name"] for col in table.get("columns", [])]
            rows = table.get("data", [])
            
            if not rows:
                logger.warning("Empty data array from Cambrian")
                return None
            
            df = pd.DataFrame(rows, columns=columns)
            
            # Standardize column names to match Pacifica format
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
            
            # Ensure proper column types
            for col in ["open", "high", "low", "close", "volume"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            
            # Sort by timestamp
            if "timestamp" in df.columns:
                df = df.sort_values("timestamp").reset_index(drop=True)
            
            logger.info(f"✅ Fetched {len(df)} candles from Cambrian")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching Cambrian OHLCV data: {e}", exc_info=True)
            return None
    
    def fetch_ohlcv_by_symbol(
        self,
        symbol: str,
        after_time: int,
        before_time: int,
        interval: str = "15m"
    ) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data by Pacifica symbol (looks up token address automatically)
        
        Args:
            symbol: Pacifica symbol (e.g., "SOL", "ETH", "BTC")
            after_time: Unix timestamp (seconds) - start time
            before_time: Unix timestamp (seconds) - end time
            interval: Candle interval (1m, 5m, 15m, 1h, 4h, 1d)
            
        Returns:
            DataFrame with OHLCV data, or None if fetch fails
        """
        token_address = self.get_token_address(symbol)
        
        if not token_address:
            logger.error(f"Cannot fetch data for {symbol} - token address not found")
            return None
        
        return self.fetch_ohlcv(token_address, after_time, before_time, interval)


