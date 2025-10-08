#!/usr/bin/env python3
"""
Test Cambrian API endpoints to explore available data
"""
import os
import requests
import json
from dotenv import load_dotenv

# Load API key from .env
load_dotenv()
API_KEY = os.getenv("CAMBRIAN_API_KEY", "doug.ZbEScx8M4zlf7kDn")
BASE_URL = "https://opabinia.cambrian.org"

# Focus tokens
FOCUS_TOKENS = ["XPL", "PENGU", "SOL", "BTC", "ETH", "HYPE", "ASTER"]

def test_endpoint(path: str, params: dict = None):
    """Test an API endpoint"""
    url = f"{BASE_URL}{path}"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    print(f"\n{'='*60}")
    print(f"Testing: {path}")
    print(f"Params: {params}")
    print('='*60)

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Response (first 500 chars):")
            print(json.dumps(data, indent=2)[:500])
            return data
        else:
            print(f"Error: {response.text}")
            return None

    except Exception as e:
        print(f"Exception: {e}")
        return None

if __name__ == "__main__":
    print("Cambrian API Explorer")
    print("=" * 60)

    # Try common API paths (from knowledge base results)
    endpoints = [
        "/api/v1/solana/tokens",
        "/api/v1/solana/ohlcv/base-quote",
        "/api/v1/solana/wallet-balance-history",
        "/api/v1/solana/trending_tokens",
        "/api/v1/solana/traders/leaderboard",
        "/api/v1/solana/trade-statistics",
        "/api/v1/solana/tokens/security",
        "/api/v1/solana/tokens/holders_over_time",
        "/api/v1/solana/tokens/holder_distribution_over_time",
    ]

    for endpoint in endpoints:
        test_endpoint(endpoint)

    # Try with symbols parameter
    symbols_param = ",".join(FOCUS_TOKENS)
    test_endpoint("/v1/perp/risk-engine", {"symbols": symbols_param})

    print(f"\n{'='*60}")
    print("Exploration complete")
    print('='*60)
