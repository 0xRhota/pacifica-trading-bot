#!/usr/bin/env python3
"""
Test Pacifica API order placement to diagnose the text/plain error
"""
import asyncio
import aiohttp
import json
import time
import hmac
import hashlib
import base64
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.pacifica.fi/api/v1"
API_KEY = os.getenv("PACIFICA_API_KEY")
ACCOUNT = os.getenv("PACIFICA_ACCOUNT")

def generate_signature(api_key: str, timestamp: str, method: str, path: str, body: str = "") -> str:
    """Generate API signature for authentication"""
    message = timestamp + method + path + body
    signature = hmac.new(
        api_key.encode(),
        message.encode(),
        hashlib.sha256
    ).digest()
    return base64.b64encode(signature).decode()

async def test_order():
    """Test order placement"""
    if not API_KEY or not ACCOUNT:
        print("❌ PACIFICA_API_KEY or PACIFICA_ACCOUNT not set in .env")
        return

    print(f"✅ API Key loaded: {API_KEY[:10]}...")
    print(f"✅ Account: {ACCOUNT}")

    endpoint = "/orders/create_market"
    method = "POST"

    # Small test order - Pacifica uses "bid" (long) and "ask" (short)
    data = {
        "account": ACCOUNT,  # Account address
        "symbol": "SOL",
        "side": "bid",  # "bid" = long/buy, "ask" = short/sell
        "order_type": "market",
        "amount": "0.01",  # Tiny size for testing (~$2) - must be string
        "reduce_only": False,  # False = open new position, True = close existing only
        "slippage_percent": "1.0"  # Allow 1% slippage - must be string
    }

    timestamp = str(int(time.time() * 1000))
    body = json.dumps(data)
    signature = generate_signature(API_KEY, timestamp, method, endpoint, body)

    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": API_KEY,
        "X-TIMESTAMP": timestamp,
        "X-SIGNATURE": signature
    }

    url = f"{BASE_URL}{endpoint}"

    print(f"\n🔧 Testing order placement...")
    print(f"URL: {url}")
    print(f"Headers: {headers}")
    print(f"Body: {body}")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, data=body) as response:
                status = response.status
                content_type = response.headers.get('Content-Type', 'unknown')

                print(f"\n📊 Response:")
                print(f"Status: {status}")
                print(f"Content-Type: {content_type}")

                # Try to read response regardless of content type
                text = await response.text()
                print(f"Body: {text}")

                if status == 200:
                    print("✅ Order placement successful!")
                else:
                    print(f"❌ Order placement failed (status {status})")

        except Exception as e:
            print(f"❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_order())
