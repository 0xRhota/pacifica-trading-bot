"""
Solana Token Address Mapping for Pacifica Perpetuals
Maps Pacifica symbol → Solana token address for Cambrian API

Status: PARTIAL - not all tokens have known addresses
"""

# Known Solana token addresses (verified)
SOLANA_TOKEN_ADDRESSES = {
    # Native/Wrapped major tokens
    "SOL": "So11111111111111111111111111111111111111112",  # Wrapped SOL
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC

    # Common tokens (need to verify these)
    "BTC": None,  # Wrapped BTC - address unknown
    "ETH": None,  # Wrapped ETH - address unknown
    "BNB": None,  # Wrapped BNB - address unknown
    "DOGE": None,  # Wrapped DOGE - address unknown
    "XRP": None,  # Wrapped XRP - address unknown
    "LTC": None,  # Wrapped LTC - address unknown
    "AVAX": None,  # Wrapped AVAX - address unknown

    # Solana native tokens (need addresses)
    "BONK": None,  # kBONK on Pacifica
    "PENGU": None,
    "PUMP": None,
    "HYPE": None,
    "FARTCOIN": None,
    "ENA": None,
    "SUI": None,  # Might be wrapped
    "AAVE": None,
    "LINK": None,
    "PEPE": None,  # kPEPE on Pacifica
    "LDO": None,
    "UNI": None,
    "CRV": None,
    "WLFI": None,
    "ASTER": None,
    "XPL": None,
    "2Z": None,
    "PAXG": None,
    "ZEC": None,
    "MON": None,
}

# All 28 Pacifica markets (from /info endpoint)
PACIFICA_SYMBOLS = [
    "ETH", "BTC", "SOL", "PUMP", "XRP", "HYPE", "DOGE", "FARTCOIN",
    "ENA", "BNB", "SUI", "kBONK", "PENGU", "AAVE", "LINK", "kPEPE",
    "LTC", "LDO", "UNI", "CRV", "WLFI", "AVAX", "ASTER", "XPL",
    "2Z", "PAXG", "ZEC", "MON"
]

def get_token_address(symbol: str):
    """
    Get Solana token address for a Pacifica symbol

    Args:
        symbol: Pacifica symbol (e.g., "SOL", "kBONK")

    Returns:
        Solana token address or None if not mapped
    """
    # Handle kBONK/kPEPE naming difference
    if symbol == "kBONK":
        symbol = "BONK"
    elif symbol == "kPEPE":
        symbol = "PEPE"

    return SOLANA_TOKEN_ADDRESSES.get(symbol)

def get_mapped_symbols():
    """Get list of Pacifica symbols that have known Solana addresses"""
    return [sym for sym in PACIFICA_SYMBOLS if get_token_address(sym) is not None]

def get_unmapped_symbols():
    """Get list of Pacifica symbols without Solana addresses"""
    return [sym for sym in PACIFICA_SYMBOLS if get_token_address(sym) is None]

if __name__ == "__main__":
    mapped = get_mapped_symbols()
    unmapped = get_unmapped_symbols()

    print(f"✅ Mapped tokens ({len(mapped)}/28):")
    for sym in mapped:
        print(f"   {sym}: {get_token_address(sym)}")

    print(f"\n❌ Unmapped tokens ({len(unmapped)}/28):")
    print(f"   {', '.join(unmapped)}")

    print(f"\n📊 Coverage: {len(mapped)/len(PACIFICA_SYMBOLS)*100:.1f}%")
