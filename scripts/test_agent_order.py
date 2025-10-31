#!/usr/bin/env python3
"""
Test Pacifica order placement using API Agent Keys (correct method)
Based on: https://github.com/pacifica-fi/python-sdk/blob/main/rest/api_agent_keys.py
"""
import requests
import json
import time
import uuid
import os
from dotenv import load_dotenv
from solders.keypair import Keypair

load_dotenv()

# Load from .env
ACCOUNT = os.getenv("PACIFICA_ACCOUNT")  # Main account public key
AGENT_PRIVATE_KEY = os.getenv("PACIFICA_API_KEY")  # Agent wallet private key
BASE_URL = "https://api.pacifica.fi/api/v1"

if not ACCOUNT or not AGENT_PRIVATE_KEY:
    print("❌ Missing PACIFICA_ACCOUNT or PACIFICA_API_KEY in .env")
    exit(1)

# Get agent wallet public key from private key
agent_keypair = Keypair.from_base58_string(AGENT_PRIVATE_KEY)
agent_public_key = str(agent_keypair.pubkey())

print(f"✅ Main Account: {ACCOUNT}")
print(f"✅ Agent Public Key: {agent_public_key}")

def sort_json_keys(value):
    """Sort JSON keys recursively"""
    if isinstance(value, dict):
        sorted_dict = {}
        for key in sorted(value.keys()):
            sorted_dict[key] = sort_json_keys(value[key])
        return sorted_dict
    elif isinstance(value, list):
        return [sort_json_keys(item) for item in value]
    else:
        return value

def sign_message(header, payload, private_key_b58):
    """Sign message with agent wallet"""
    # Combine header and payload
    data = {
        **header,
        "data": payload,
    }

    # Sort keys and create compact JSON
    message = sort_json_keys(data)
    message_json = json.dumps(message, separators=(",", ":"))

    # Sign with agent wallet
    keypair = Keypair.from_base58_string(private_key_b58)
    signature = keypair.sign_message(message_json.encode("utf-8"))

    import base58
    return (message_json, base58.b58encode(bytes(signature)).decode("ascii"))

# Create signature header
timestamp = int(time.time() * 1_000)

signature_header = {
    "timestamp": timestamp,
    "expiry_window": 5_000,
    "type": "create_market_order",
}

# Construct signature payload
signature_payload = {
    "symbol": "SOL",
    "reduce_only": False,
    "amount": "0.06",  # ~$12 (min is $10)
    "side": "bid",
    "slippage_percent": "1.0",
    "client_order_id": str(uuid.uuid4()),
}

# Sign with agent wallet
message, signature = sign_message(signature_header, signature_payload, AGENT_PRIVATE_KEY)

# Construct request
request_header = {
    "account": ACCOUNT,  # Main account
    "agent_wallet": agent_public_key,  # Agent wallet public key
    "signature": signature,
    "timestamp": signature_header["timestamp"],
    "expiry_window": signature_header["expiry_window"],
}

request = {
    **request_header,
    **signature_payload,
}

# Send request
url = f"{BASE_URL}/orders/create_market"
headers = {"Content-Type": "application/json"}

print(f"\n🔧 Testing order placement...")
print(f"URL: {url}")
print(f"Request: {json.dumps(request, indent=2)}")

response = requests.post(url, json=request, headers=headers)

print(f"\n📊 Response:")
print(f"Status: {response.status_code}")
print(f"Body: {response.text}")

if response.status_code == 200:
    print("✅ Order placement successful!")
else:
    print(f"❌ Order placement failed")
