#!/usr/bin/env python3
"""
Get the public key from API Agent private key
"""
import os
from dotenv import load_dotenv
from solders.keypair import Keypair

load_dotenv()

api_key = os.getenv("PACIFICA_API_KEY")
if not api_key:
    print("❌ PACIFICA_API_KEY not found in .env")
    exit(1)

try:
    keypair = Keypair.from_base58_string(api_key)
    pubkey = str(keypair.pubkey())
    print(f"✅ API Agent Private Key: {api_key[:10]}...")
    print(f"✅ API Agent Public Key: {pubkey}")
    print(f"\nAdd this to .env:")
    print(f'PACIFICA_AGENT_PUBLIC="{pubkey}"')
except Exception as e:
    print(f"❌ Error: {e}")
    print("API key might not be a valid Solana private key")
