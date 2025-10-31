"""
Open Interest (OI) Data Fetcher
Fetches OI data from Binance (priority) and HyperLiquid (fallback)

Coverage: 26/28 Pacifica markets (92.9%)
- Binance: 19 markets
- HyperLiquid: 26 markets (7 not on Binance)
- Missing: kBONK, kPEPE

Usage:
    fetcher = OIDataFetcher()
    oi_values = fetcher.fetch_all_oi(pacifica_symbols)
"""

import requests
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class OIDataFetcher:
    """Fetch Open Interest data from multiple sources"""

    # Symbol mapping: Pacifica → Binance USDT perpetuals
    BINANCE_SYMBOL_MAP = {
        "ETH": "ETHUSDT",
        "BTC": "BTCUSDT",
        "SOL": "SOLUSDT",
        "XRP": "XRPUSDT",
        "HYPE": "HYPEUSDT",
        "DOGE": "DOGEUSDT",
        "ENA": "ENAUSDT",
        "BNB": "BNBUSDT",
        "SUI": "SUIUSDT",
        "PENGU": "PENGUUSDT",
        "AAVE": "AAVEUSDT",
        "LINK": "LINKUSDT",
        "LTC": "LTCUSDT",
        "LDO": "LDOUSDT",
        "UNI": "UNIUSDT",
        "CRV": "CRVUSDT",
        "AVAX": "AVAXUSDT",
        "PAXG": "PAXGUSDT",
        "ZEC": "ZECUSDT",
    }

    # HyperLiquid symbol mapping (most are 1:1, except kBONK/kPEPE)
    HYPERLIQUID_SYMBOL_MAP = {
        "kBONK": "BONK",  # Not available on HyperLiquid
        "kPEPE": "PEPE",  # Not available on HyperLiquid
    }

    def __init__(self):
        self.binance_url = "https://fapi.binance.com/fapi/v1/openInterest"
        self.hyperliquid_url = "https://api.hyperliquid.xyz/info"
        self._hl_cache = None  # Cache HyperLiquid data (updates every call)

    def fetch_binance_oi(self, symbol: str) -> Optional[float]:
        """
        Fetch OI from Binance Futures

        Args:
            symbol: Pacifica symbol (e.g., "SOL")

        Returns:
            OI value or None if unavailable
        """
        binance_symbol = self.BINANCE_SYMBOL_MAP.get(symbol)
        if not binance_symbol:
            return None

        try:
            response = requests.get(
                self.binance_url,
                params={"symbol": binance_symbol},
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                return float(data.get("openInterest", 0))
            else:
                logger.warning(f"Binance OI fetch failed for {symbol}: HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Binance OI error for {symbol}: {e}")
            return None

    def fetch_hyperliquid_data(self) -> Dict[str, float]:
        """
        Fetch all HyperLiquid market data (call once per cycle)

        Returns:
            Dict mapping symbol → OI value
        """
        try:
            response = requests.post(
                self.hyperliquid_url,
                json={"type": "metaAndAssetCtxs"},
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                meta = data[0]
                contexts = data[1]

                # Build symbol → OI mapping
                oi_map = {}
                for i, market in enumerate(meta['universe']):
                    symbol = market['name']
                    if i < len(contexts):
                        oi = contexts[i].get('openInterest')
                        if oi:
                            oi_map[symbol] = float(oi)

                logger.info(f"✅ HyperLiquid: Fetched OI for {len(oi_map)} markets")
                return oi_map
            else:
                logger.warning(f"HyperLiquid fetch failed: HTTP {response.status_code}")
                return {}

        except Exception as e:
            logger.error(f"HyperLiquid error: {e}")
            return {}

    def get_hyperliquid_oi(self, symbol: str) -> Optional[float]:
        """
        Get OI from HyperLiquid cache

        Args:
            symbol: Pacifica symbol (e.g., "SOL")

        Returns:
            OI value or None if unavailable
        """
        # Use cache if available
        if self._hl_cache is None:
            self._hl_cache = self.fetch_hyperliquid_data()

        # Handle kBONK/kPEPE naming
        hl_symbol = self.HYPERLIQUID_SYMBOL_MAP.get(symbol, symbol)
        return self._hl_cache.get(hl_symbol)

    def fetch_oi(self, symbol: str) -> Optional[float]:
        """
        Fetch OI for a single symbol (Binance priority, HyperLiquid fallback)

        Args:
            symbol: Pacifica symbol (e.g., "SOL")

        Returns:
            OI value or None if unavailable
        """
        # Try Binance first (faster, more reliable)
        oi = self.fetch_binance_oi(symbol)
        if oi is not None:
            return oi

        # Fallback to HyperLiquid
        oi = self.get_hyperliquid_oi(symbol)
        if oi is not None:
            return oi

        # No data available
        logger.warning(f"⚠️ No OI data for {symbol}")
        return None

    def fetch_all_oi(self, symbols: list) -> Dict[str, Optional[float]]:
        """
        Fetch OI for multiple symbols (batch operation)

        Args:
            symbols: List of Pacifica symbols

        Returns:
            Dict mapping symbol → OI value (None if unavailable)
        """
        # Pre-fetch HyperLiquid data (single API call)
        self._hl_cache = self.fetch_hyperliquid_data()

        # Fetch OI for each symbol
        results = {}
        for symbol in symbols:
            results[symbol] = self.fetch_oi(symbol)

        # Clear cache after batch
        self._hl_cache = None

        return results


if __name__ == "__main__":
    # Test with all 28 Pacifica markets
    logging.basicConfig(level=logging.INFO)

    PACIFICA_SYMBOLS = [
        "ETH", "BTC", "SOL", "PUMP", "XRP", "HYPE", "DOGE", "FARTCOIN",
        "ENA", "BNB", "SUI", "kBONK", "PENGU", "AAVE", "LINK", "kPEPE",
        "LTC", "LDO", "UNI", "CRV", "WLFI", "AVAX", "ASTER", "XPL",
        "2Z", "PAXG", "ZEC", "MON"
    ]

    fetcher = OIDataFetcher()
    oi_data = fetcher.fetch_all_oi(PACIFICA_SYMBOLS)

    print("\n" + "=" * 60)
    print("Open Interest Data")
    print("=" * 60)

    available = 0
    for symbol in PACIFICA_SYMBOLS:
        oi = oi_data.get(symbol)
        if oi is not None:
            print(f"{symbol:<10} {oi:>20,.2f}")
            available += 1
        else:
            print(f"{symbol:<10} {'N/A':>20}")

    print("=" * 60)
    print(f"Coverage: {available}/{len(PACIFICA_SYMBOLS)} ({available/len(PACIFICA_SYMBOLS)*100:.1f}%)")
