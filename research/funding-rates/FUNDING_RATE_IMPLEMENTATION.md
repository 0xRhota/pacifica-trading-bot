# Funding Rate Implementation Guide

**Ready-to-use code patterns for integrating funding rates into your bot**

---

## Pattern 1: Simple Binance Polling (5 minutes to integrate)

```python
import requests
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class BinanceFundingRateClient:
    """Fetch funding rates from Binance Futures API"""
    
    BASE_URL = "https://fapi.binance.com/fapi/v1"
    
    def get_funding_rate(self, symbol: str) -> Optional[Dict]:
        """
        Get current funding rate for a symbol
        
        Args:
            symbol: Trading pair (e.g., 'SOL', 'BTC', 'ETH')
        
        Returns:
            {
                'symbol': 'SOLUSDT',
                'fundingRate': '0.00016840',
                'fundingTime': 1699999999000
            }
        """
        try:
            url = f"{self.BASE_URL}/fundingRate"
            params = {"symbol": f"{symbol}USDT"}
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch funding rate for {symbol}: {e}")
            return None
    
    def get_funding_rate_history(self, symbol: str, limit: int = 10) -> Optional[list]:
        """Get historical funding rates"""
        try:
            url = f"{self.BASE_URL}/fundingRateHist"
            params = {"symbol": f"{symbol}USDT", "limit": limit}
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch funding rate history for {symbol}: {e}")
            return None
    
    def get_multiple_rates(self, symbols: list) -> Dict[str, Dict]:
        """Get funding rates for multiple symbols at once"""
        rates = {}
        for symbol in symbols:
            rate = self.get_funding_rate(symbol)
            if rate:
                rates[symbol] = rate
        return rates


# Usage Example
if __name__ == "__main__":
    client = BinanceFundingRateClient()
    
    # Get single rate
    sol_rate = client.get_funding_rate("SOL")
    print(f"SOL Funding Rate: {sol_rate}")
    
    # Get multiple rates
    rates = client.get_multiple_rates(["SOL", "BTC", "ETH"])
    for symbol, rate in rates.items():
        print(f"{symbol}: {rate['fundingRate']}")
```

---

## Pattern 2: Multi-Source with Fallback (More Robust)

```python
from enum import Enum
from typing import Dict, Optional
import requests
import logging

logger = logging.getLogger(__name__)

class FundingRateSource(Enum):
    BINANCE = "binance"
    BYBIT = "bybit"
    OKX = "okx"
    DRIFT = "drift"


class MultiFundingRateClient:
    """Fetch funding rates from multiple sources with fallback"""
    
    SOURCES = {
        FundingRateSource.BINANCE: {
            "url": "https://fapi.binance.com/fapi/v1/fundingRate",
            "symbol_format": "{symbol}USDT"
        },
        FundingRateSource.BYBIT: {
            "url": "https://api.bybit.com/v5/market/funding/history",
            "symbol_format": "{symbol}USDT",
            "params": {"category": "linear", "limit": "1"}
        },
        FundingRateSource.OKX: {
            "url": "https://www.okx.com/api/v5/public/funding-rate",
            "symbol_format": "{symbol}-USDT-SWAP"
        }
    }
    
    def get_funding_rate(self, symbol: str, source: Optional[FundingRateSource] = None) -> Optional[Dict]:
        """Get funding rate from specified source or try fallback"""
        
        if source:
            # Try specific source
            return self._query_source(symbol, source)
        
        # Try sources in order
        for src in [FundingRateSource.BINANCE, FundingRateSource.BYBIT, FundingRateSource.OKX]:
            try:
                rate = self._query_source(symbol, src)
                if rate:
                    return rate
            except Exception as e:
                logger.warning(f"{src.value} failed: {e}")
                continue
        
        logger.error(f"All sources failed for {symbol}")
        return None
    
    def _query_source(self, symbol: str, source: FundingRateSource) -> Optional[Dict]:
        """Query a specific source"""
        
        if source == FundingRateSource.BINANCE:
            return self._query_binance(symbol)
        elif source == FundingRateSource.BYBIT:
            return self._query_bybit(symbol)
        elif source == FundingRateSource.OKX:
            return self._query_okx(symbol)
        
        return None
    
    def _query_binance(self, symbol: str) -> Optional[Dict]:
        url = self.SOURCES[FundingRateSource.BINANCE]["url"]
        symbol_str = self.SOURCES[FundingRateSource.BINANCE]["symbol_format"].format(symbol=symbol)
        response = requests.get(url, params={"symbol": symbol_str}, timeout=5)
        response.raise_for_status()
        return response.json()
    
    def _query_bybit(self, symbol: str) -> Optional[Dict]:
        url = self.SOURCES[FundingRateSource.BYBIT]["url"]
        symbol_str = self.SOURCES[FundingRateSource.BYBIT]["symbol_format"].format(symbol=symbol)
        params = {**self.SOURCES[FundingRateSource.BYBIT]["params"], "symbol": symbol_str}
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data.get("result") and data["result"].get("list"):
            return data["result"]["list"][0]
        return None
    
    def _query_okx(self, symbol: str) -> Optional[Dict]:
        url = self.SOURCES[FundingRateSource.OKX]["url"]
        inst_id = self.SOURCES[FundingRateSource.OKX]["symbol_format"].format(symbol=symbol)
        response = requests.get(url, params={"instId": inst_id}, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data.get("data"):
            return data["data"][0]
        return None


# Usage Example
if __name__ == "__main__":
    client = MultiFundingRateClient()
    
    # Try best source automatically
    rate = client.get_funding_rate("SOL")
    print(f"SOL Rate (auto-source): {rate}")
    
    # Try specific source
    binance_rate = client.get_funding_rate("SOL", FundingRateSource.BINANCE)
    print(f"SOL Rate (Binance): {binance_rate}")
```

---

## Pattern 3: Rate Comparison Across Exchanges

```python
from typing import Dict, List
import requests

class FundingRateComparison:
    """Compare funding rates across exchanges to find best deal"""
    
    SOURCES = {
        "binance": {
            "url": "https://fapi.binance.com/fapi/v1/fundingRate",
            "format": lambda s: f"{s}USDT",
            "key": "fundingRate"
        },
        "bybit": {
            "url": "https://api.bybit.com/v5/market/funding/history",
            "format": lambda s: f"{s}USDT",
            "key": "fundingRate",
            "params": {"category": "linear", "limit": "1"}
        },
        "okx": {
            "url": "https://www.okx.com/api/v5/public/funding-rate",
            "format": lambda s: f"{s}-USDT-SWAP",
            "key": "fundingRate"
        }
    }
    
    def compare_rates(self, symbol: str) -> Dict[str, float]:
        """Compare funding rates across all sources"""
        rates = {}
        
        for source_name, config in self.SOURCES.items():
            try:
                if source_name == "binance":
                    response = requests.get(
                        config["url"],
                        params={"symbol": config["format"](symbol)},
                        timeout=5
                    )
                    data = response.json()
                    rates[source_name] = float(data[config["key"]])
                
                elif source_name == "bybit":
                    response = requests.get(
                        config["url"],
                        params={**config["params"], "symbol": config["format"](symbol)},
                        timeout=5
                    )
                    data = response.json()
                    if data.get("result") and data["result"].get("list"):
                        rates[source_name] = float(data["result"]["list"][0][config["key"]])
                
                elif source_name == "okx":
                    response = requests.get(
                        config["url"],
                        params={"instId": config["format"](symbol)},
                        timeout=5
                    )
                    data = response.json()
                    if data.get("data"):
                        rates[source_name] = float(data["data"][0][config["key"]])
            
            except Exception as e:
                print(f"Error fetching from {source_name}: {e}")
                continue
        
        return rates
    
    def best_rate(self, symbol: str) -> tuple:
        """Find the best (lowest) funding rate"""
        rates = self.compare_rates(symbol)
        if not rates:
            return None, None
        
        best_source = min(rates.items(), key=lambda x: x[1])
        return best_source[0], best_source[1]
    
    def rate_spread(self, symbol: str) -> float:
        """Calculate spread between best and worst rates"""
        rates = self.compare_rates(symbol)
        if not rates or len(rates) < 2:
            return 0
        
        rates_list = list(rates.values())
        return max(rates_list) - min(rates_list)


# Usage Example
if __name__ == "__main__":
    comparator = FundingRateComparison()
    
    symbol = "SOL"
    
    # Compare all rates
    rates = comparator.compare_rates(symbol)
    print(f"{symbol} Funding Rates:")
    for exchange, rate in rates.items():
        print(f"  {exchange}: {rate:.6f}")
    
    # Find best rate
    best_source, best_rate = comparator.best_rate(symbol)
    print(f"\nBest rate: {best_source} at {best_rate:.6f}")
    
    # Check spread
    spread = comparator.rate_spread(symbol)
    print(f"Rate spread: {spread:.6f}")
```

---

## Pattern 4: Integrate with Position Management

```python
from datetime import datetime
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class PositionWithFundingRate:
    """Position manager that considers funding rates"""
    
    def __init__(self, funding_rate_client):
        self.funding_rate_client = funding_rate_client
        self.positions = {}
    
    def open_position(self, symbol: str, side: str, size: float, entry_price: float) -> bool:
        """Open position, checking funding rates first"""
        
        # Get current funding rate
        funding_rate = self.funding_rate_client.get_funding_rate(symbol)
        if not funding_rate:
            logger.warning(f"Could not fetch funding rate for {symbol}, proceeding anyway")
            funding_rate_value = 0
        else:
            funding_rate_value = float(funding_rate.get('fundingRate', 0))
        
        # Warn if rate is high
        if abs(funding_rate_value) > 0.001:  # >0.1% per 8h
            logger.warning(f"{symbol} has high funding rate: {funding_rate_value:.4%}")
        
        # Check if side matches rate direction
        if side == "long" and funding_rate_value > 0.0005:
            logger.warning(f"Opening LONG at high positive funding rate: {funding_rate_value:.4%}")
            # Optional: skip trade or reduce size
        
        # Record position with funding rate
        self.positions[symbol] = {
            "side": side,
            "size": size,
            "entry_price": entry_price,
            "timestamp": datetime.now(),
            "funding_rate_at_entry": funding_rate_value,
            "total_funding_paid": 0
        }
        
        logger.info(f"Opened {side} position: {symbol} {size} @ {entry_price} (FR: {funding_rate_value:.4%})")
        return True
    
    def calculate_funding_cost(self, symbol: str, position_size: float, 
                             funding_rate: float, hours_held: float) -> float:
        """Calculate cost of funding for a position"""
        # Funding rate is per 8-hour period
        periods = hours_held / 8
        total_cost = position_size * funding_rate * periods
        return total_cost
    
    def get_position_pnl(self, symbol: str, current_price: float) -> Dict:
        """Calculate PnL including funding costs"""
        if symbol not in self.positions:
            return None
        
        pos = self.positions[symbol]
        
        # Calculate price PnL
        if pos["side"] == "long":
            price_pnl = (current_price - pos["entry_price"]) * pos["size"]
        else:
            price_pnl = (pos["entry_price"] - current_price) * pos["size"]
        
        # Get current funding rate
        funding = self.funding_rate_client.get_funding_rate(symbol)
        current_fr = float(funding.get('fundingRate', 0)) if funding else 0
        
        # Calculate hours held
        hours_held = (datetime.now() - pos["timestamp"]).total_seconds() / 3600
        
        # Calculate funding cost
        funding_cost = self.calculate_funding_cost(symbol, pos["size"], current_fr, hours_held)
        
        # Total PnL
        total_pnl = price_pnl - funding_cost  # Subtract cost for long, add for short
        
        return {
            "price_pnl": price_pnl,
            "funding_cost": funding_cost,
            "total_pnl": total_pnl,
            "current_funding_rate": current_fr,
            "hours_held": hours_held
        }


# Usage Example
if __name__ == "__main__":
    from Pattern1 import BinanceFundingRateClient
    
    client = BinanceFundingRateClient()
    position_manager = PositionWithFundingRate(client)
    
    # Open a position
    position_manager.open_position("SOL", "long", size=1.0, entry_price=95.00)
    
    # Check PnL after some time (simulate later)
    pnl = position_manager.get_position_pnl("SOL", current_price=96.00)
    print(f"\nPosition PnL:")
    print(f"  Price PnL: ${pnl['price_pnl']:.2f}")
    print(f"  Funding Cost: ${pnl['funding_cost']:.2f}")
    print(f"  Total PnL: ${pnl['total_pnl']:.2f}")
```

---

## Pattern 5: Caching to Reduce API Calls

```python
from datetime import datetime, timedelta
from typing import Dict, Optional
import requests

class CachedFundingRateClient:
    """Cache funding rates to reduce API calls (rates don't change often)"""
    
    def __init__(self, cache_ttl_seconds: int = 300):
        self.base_url = "https://fapi.binance.com/fapi/v1"
        self.cache = {}
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
    
    def get_funding_rate(self, symbol: str) -> Optional[Dict]:
        """Get funding rate with caching"""
        
        # Check cache
        if symbol in self.cache:
            cached_data, cached_time = self.cache[symbol]
            if datetime.now() - cached_time < self.cache_ttl:
                return cached_data  # Return cached value
        
        # Fetch fresh data
        try:
            url = f"{self.base_url}/fundingRate"
            response = requests.get(url, params={"symbol": f"{symbol}USDT"}, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            # Cache the result
            self.cache[symbol] = (data, datetime.now())
            
            return data
        
        except Exception as e:
            # Return stale cache if available
            if symbol in self.cache:
                return self.cache[symbol][0]
            return None
    
    def clear_cache(self, symbol: Optional[str] = None):
        """Clear cache for symbol(s)"""
        if symbol:
            self.cache.pop(symbol, None)
        else:
            self.cache.clear()
    
    def get_cache_age(self, symbol: str) -> Optional[float]:
        """Get age of cached data in seconds"""
        if symbol not in self.cache:
            return None
        _, cache_time = self.cache[symbol]
        return (datetime.now() - cache_time).total_seconds()


# Usage Example
if __name__ == "__main__":
    client = CachedFundingRateClient(cache_ttl_seconds=60)
    
    # First call: hits API
    rate1 = client.get_funding_rate("SOL")
    print(f"First call: {rate1}")
    
    # Second call within 60s: uses cache
    rate2 = client.get_funding_rate("SOL")
    print(f"Second call (cached): {rate2}")
    
    # Check cache age
    age = client.get_cache_age("SOL")
    print(f"Cache age: {age:.1f} seconds")
    
    # Clear cache
    client.clear_cache("SOL")
    
    # Third call: hits API again
    rate3 = client.get_funding_rate("SOL")
    print(f"Third call (after clear): {rate3}")
```

---

## Integration Checklist

Use these patterns in your bot:

1. **Start with Pattern 1** (Simple Binance client)
   - Easy to add to existing code
   - Takes 5 minutes
   - Good for understanding the flow

2. **Upgrade to Pattern 2** (Multi-source fallback)
   - More reliable
   - Automatic failover
   - Best for production

3. **Add Pattern 5** (Caching)
   - Reduces API load
   - Funding rates change slowly (every 8 hours)
   - Cache for 5-10 minutes

4. **Integrate with Pattern 4** (Position management)
   - Track funding costs in P&L
   - Avoid opening high-cost positions
   - Calculate true profitability

5. **Optional: Add Pattern 3** (Rate comparison)
   - Find best execution
   - Compare exchanges
   - Build for future multi-exchange trading

---

## Testing Commands

```bash
# Test Binance
python3 -c "
import requests
r = requests.get('https://fapi.binance.com/fapi/v1/fundingRate', params={'symbol': 'SOLUSDT'})
print(r.json())
"

# Test all sources
python3 research/FUNDING_RATE_IMPLEMENTATION.md
```

---

## File Placement

Save these patterns in:
- `/pacifica-trading-bot/utils/funding_rates.py` - Main client class
- `/pacifica-trading-bot/dexes/funding_rates/` - Exchange-specific implementations
- `/pacifica-trading-bot/tests/test_funding_rates.py` - Unit tests

