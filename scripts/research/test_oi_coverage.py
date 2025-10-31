"""
Test Open Interest (OI) data availability across exchanges
Checks which Pacifica markets have OI data on Binance and HyperLiquid
"""

import requests
import json

# All 28 Pacifica markets
PACIFICA_SYMBOLS = [
    "ETH", "BTC", "SOL", "PUMP", "XRP", "HYPE", "DOGE", "FARTCOIN",
    "ENA", "BNB", "SUI", "kBONK", "PENGU", "AAVE", "LINK", "kPEPE",
    "LTC", "LDO", "UNI", "CRV", "WLFI", "AVAX", "ASTER", "XPL",
    "2Z", "PAXG", "ZEC", "MON"
]

# Symbol mapping to Binance (USDT perpetuals)
BINANCE_SYMBOL_MAP = {
    "ETH": "ETHUSDT",
    "BTC": "BTCUSDT",
    "SOL": "SOLUSDT",
    "PUMP": None,  # Not on Binance
    "XRP": "XRPUSDT",
    "HYPE": "HYPEUSDT",
    "DOGE": "DOGEUSDT",
    "FARTCOIN": None,
    "ENA": "ENAUSDT",
    "BNB": "BNBUSDT",
    "SUI": "SUIUSDT",
    "kBONK": "BONKUSDT",
    "PENGU": "PENGUUSDT",
    "AAVE": "AAVEUSDT",
    "LINK": "LINKUSDT",
    "kPEPE": "PEPEUSDT",
    "LTC": "LTCUSDT",
    "LDO": "LDOUSDT",
    "UNI": "UNIUSDT",
    "CRV": "CRVUSDT",
    "WLFI": None,
    "AVAX": "AVAXUSDT",
    "ASTER": None,
    "XPL": None,
    "2Z": None,
    "PAXG": "PAXGUSDT",
    "ZEC": "ZECUSDT",
    "MON": None,
}

def test_binance_oi(symbol):
    """Test if Binance has OI data for a symbol"""
    binance_symbol = BINANCE_SYMBOL_MAP.get(symbol)
    if not binance_symbol:
        return None, "No Binance mapping"

    try:
        url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={binance_symbol}"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            oi = data.get("openInterest")
            return float(oi), "✅ Available"
        else:
            return None, f"❌ HTTP {response.status_code}"
    except Exception as e:
        return None, f"❌ Error: {str(e)[:50]}"

def get_hyperliquid_data():
    """Get all HyperLiquid market data including OI"""
    try:
        url = "https://api.hyperliquid.xyz/info"
        payload = {"type": "metaAndAssetCtxs"}
        response = requests.post(url, json=payload, timeout=5)

        if response.status_code == 200:
            data = response.json()
            # data[0] = meta (universe), data[1] = assetCtxs (market data)
            meta = data[0]
            contexts = data[1]

            # Build symbol -> OI mapping
            oi_map = {}
            for i, market in enumerate(meta['universe']):
                symbol = market['name']
                if i < len(contexts):
                    oi = contexts[i].get('openInterest')
                    oi_map[symbol] = float(oi) if oi else None

            return oi_map
        else:
            return {}
    except Exception as e:
        print(f"❌ HyperLiquid error: {e}")
        return {}

def test_hyperliquid_oi(symbol, hl_data):
    """Check if HyperLiquid has OI for a symbol"""
    # Handle kBONK/kPEPE naming
    hl_symbol = symbol
    if symbol == "kBONK":
        hl_symbol = "BONK"
    elif symbol == "kPEPE":
        hl_symbol = "PEPE"

    if hl_symbol in hl_data:
        oi = hl_data[hl_symbol]
        return oi, "✅ Available" if oi else "⚠️ No data"
    else:
        return None, "❌ Not listed"

if __name__ == "__main__":
    print("=" * 80)
    print("Open Interest (OI) Data Coverage Report")
    print("=" * 80)
    print()

    # Fetch HyperLiquid data once
    print("Fetching HyperLiquid data...")
    hl_data = get_hyperliquid_data()
    print(f"✅ HyperLiquid: {len(hl_data)} markets found")
    print()

    # Test coverage
    results = []
    for symbol in PACIFICA_SYMBOLS:
        binance_oi, binance_status = test_binance_oi(symbol)
        hl_oi, hl_status = test_hyperliquid_oi(symbol, hl_data)

        # Determine best source
        if binance_oi is not None:
            best_source = "Binance"
            best_oi = binance_oi
        elif hl_oi is not None:
            best_source = "HyperLiquid"
            best_oi = hl_oi
        else:
            best_source = "NONE"
            best_oi = None

        results.append({
            "symbol": symbol,
            "binance_status": binance_status,
            "binance_oi": binance_oi,
            "hl_status": hl_status,
            "hl_oi": hl_oi,
            "best_source": best_source,
            "best_oi": best_oi
        })

    # Print table
    print(f"{'Symbol':<10} {'Binance':<20} {'HyperLiquid':<20} {'Best Source':<15} {'OI Value':<15}")
    print("-" * 80)

    covered = 0
    for r in results:
        binance_str = f"{r['binance_status']}"
        hl_str = f"{r['hl_status']}"

        if r['best_oi'] is not None:
            oi_str = f"{r['best_oi']:,.2f}"
            covered += 1
        else:
            oi_str = "-"

        print(f"{r['symbol']:<10} {binance_str:<20} {hl_str:<20} {r['best_source']:<15} {oi_str:<15}")

    print("-" * 80)
    print(f"\n✅ Coverage: {covered}/{len(PACIFICA_SYMBOLS)} markets ({covered/len(PACIFICA_SYMBOLS)*100:.1f}%)")
    print(f"   Binance: {sum(1 for r in results if r['binance_oi'] is not None)}")
    print(f"   HyperLiquid: {sum(1 for r in results if r['hl_oi'] is not None)}")
    print(f"   Unavailable: {len(PACIFICA_SYMBOLS) - covered}")
