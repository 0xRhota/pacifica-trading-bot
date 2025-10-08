#!/usr/bin/env python3
"""
Cambrian API Client for Perps Trading Signals
Focus: Major tokens (SOL, BTC, ETH, PENGU, XPL, HYPE, ASTER)
"""
import os
import requests
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment
load_dotenv()

class CambrianClient:
    """Client for Cambrian API focused on perps trading signals"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("CAMBRIAN_API_KEY")
        self.base_url = "https://opabinia.cambrian.network"
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

        # Token addresses for focus tokens
        self.TOKENS = {
            "SOL": "So11111111111111111111111111111111111111112",
            "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            # Add others as we discover their addresses
            "BTC": None,  # Wrapped BTC on Solana
            "ETH": None,  # Wrapped ETH on Solana
            "PENGU": None,
            "XPL": None,
            "HYPE": None,
            "ASTER": None,
        }

    def _get(self, endpoint: str, params: Dict = None) -> Dict:
        """Make GET request to Cambrian API"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Error: {e}")
            return None

    def get_trade_statistics(self,
                           token_addresses: List[str],
                           timeframe: str = "24h") -> Dict:
        """
        Get trade statistics for tokens

        Args:
            token_addresses: List of token mint addresses
            timeframe: Time interval (1h, 4h, 12h, 24h, 7d)

        Returns:
            Trade statistics including buy/sell volume, counts, ratios
        """
        params = {
            "token_addresses": ",".join(token_addresses),
            "timeframe": timeframe
        }
        return self._get("/api/v1/solana/trade-statistics", params)

    def get_ohlcv(self,
                  base_address: str,
                  quote_address: str,
                  interval: str = "1h",
                  hours_back: int = 24) -> Dict:
        """
        Get OHLCV data for token pair

        Args:
            base_address: Base token mint address
            quote_address: Quote token mint address (usually USDC)
            interval: Time interval (1m, 5m, 15m, 1h, 4h, 1d)
            hours_back: How many hours of historical data

        Returns:
            OHLCV data with price, volume, trade count
        """
        before_time = int(time.time())
        after_time = before_time - (hours_back * 3600)

        params = {
            "base_address": base_address,
            "quote_address": quote_address,
            "after_time": after_time,
            "before_time": before_time,
            "interval": interval
        }
        return self._get("/api/v1/solana/ohlcv/base-quote", params)

    def get_trending_tokens(self,
                          order_by: str = "volume_24h",
                          limit: int = 100) -> Dict:
        """
        Get trending tokens ordered by specified metric

        Args:
            order_by: Sorting criteria (price_change_24h, volume_24h, current_price)
            limit: Max results (1-1000)

        Returns:
            List of trending tokens with price, volume, liquidity data
        """
        params = {
            "order_by": order_by,
            "limit": limit
        }
        return self._get("/api/v1/solana/trending_tokens", params)

    def get_token_security(self, token_address: str) -> Dict:
        """Get security metrics for a token"""
        params = {"token_address": token_address}
        return self._get("/api/v1/solana/tokens/security", params)

    def get_trader_leaderboard(self,
                              token_address: str,
                              timeframe: str = "24h",
                              limit: int = 100) -> Dict:
        """
        Get top traders for a token

        Args:
            token_address: Token mint address
            timeframe: Time interval
            limit: Max traders to return

        Returns:
            Leaderboard of top traders with PnL and trade stats
        """
        params = {
            "token_address": token_address,
            "timeframe": timeframe,
            "limit": limit
        }
        return self._get("/api/v1/solana/traders/leaderboard", params)

    # === TRADING SIGNAL METHODS ===

    def get_momentum_signal(self, symbol: str) -> Dict:
        """
        Get momentum-based trading signal for a token

        Analyzes:
        - Price change trends
        - Volume trends
        - Buy/sell pressure

        Returns signal: bullish, bearish, or neutral
        """
        token_addr = self.TOKENS.get(symbol)
        if not token_addr:
            return {"error": f"Unknown token: {symbol}"}

        # Get trade stats
        stats = self.get_trade_statistics([token_addr], "24h")
        if not stats or not stats[0]["data"]:
            return {"error": "No data available"}

        data = stats[0]["data"][0]
        buy_to_sell_ratio = data[11]  # buyToSellRatio

        # Simple momentum signal based on buy/sell pressure
        if buy_to_sell_ratio is None:
            signal = "neutral"
        elif buy_to_sell_ratio > 1.1:
            signal = "bullish"
        elif buy_to_sell_ratio < 0.9:
            signal = "bearish"
        else:
            signal = "neutral"

        return {
            "symbol": symbol,
            "signal": signal,
            "buy_to_sell_ratio": buy_to_sell_ratio,
            "volume_24h_usd": data[10],  # totalVolumeUSD
            "buy_count": data[2],  # buyCount
            "sell_count": data[3],  # sellCount
            "timestamp": datetime.now().isoformat()
        }

    def get_perps_signals(self, symbols: List[str] = None) -> List[Dict]:
        """
        Get trading signals for perps trading

        Args:
            symbols: List of token symbols to analyze (defaults to all focus tokens)

        Returns:
            List of trading signals with recommendations
        """
        if symbols is None:
            symbols = ["SOL", "BTC", "ETH"]  # Focus on majors with known addresses

        signals = []
        for symbol in symbols:
            signal = self.get_momentum_signal(symbol)
            signals.append(signal)

        return signals

if __name__ == "__main__":
    # Test the client
    client = CambrianClient()

    print("=" * 60)
    print("Cambrian API Client Test")
    print("=" * 60)

    # Test trade statistics
    print("\n📊 SOL Trade Statistics (24h):")
    stats = client.get_trade_statistics([client.TOKENS["SOL"]], "24h")
    if stats and stats[0]["data"]:
        data = stats[0]["data"][0]
        print(f"  Buy Count: {data[2]:,}")
        print(f"  Sell Count: {data[3]:,}")
        print(f"  Total Volume (USD): ${data[10]:,.0f}")
        print(f"  Buy/Sell Ratio: {data[11]:.4f}")

    # Test momentum signal
    print("\n🎯 SOL Momentum Signal:")
    signal = client.get_momentum_signal("SOL")
    print(f"  Signal: {signal.get('signal', 'N/A').upper()}")
    print(f"  Buy/Sell Ratio: {signal.get('buy_to_sell_ratio', 0):.4f}")
    print(f"  24h Volume: ${signal.get('volume_24h_usd', 0):,.0f}")

    print("\n" + "=" * 60)
