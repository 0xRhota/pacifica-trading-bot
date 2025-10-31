#!/usr/bin/env python3
"""
Generate a new Solana keypair for Pacifica API Agent Key
"""
from solders.keypair import Keypair
import base58

# Generate new keypair
keypair = Keypair()

# Get keys
private_key_bytes = bytes(keypair)  # 64 bytes
private_key_b58 = base58.b58encode(private_key_bytes).decode('ascii')
public_key = str(keypair.pubkey())

print("=" * 80)
print("NEW API AGENT KEY GENERATED")
print("=" * 80)
print(f"\n📋 Private Key (base58): {private_key_b58}")
print(f"\n📋 Public Key: {public_key}")
print("\n" + "=" * 80)
print("INSTRUCTIONS:")
print("=" * 80)
print("1. Copy the Private Key above")
print("2. Go to Pacifica website → API Agent Keys")
print("3. Paste it in the 'Enter a desired base58 private key' field")
print("4. Click 'Create' to register it")
print("5. Add to your .env file:")
print(f'   PACIFICA_API_KEY="{private_key_b58}"')
print("=" * 80)
