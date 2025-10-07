"""
Pacifica SDK integration - handles signing and order placement
Based on official Pacifica Python SDK
"""

import json
import time
import uuid
import base58
from typing import Optional, Dict
from solders.keypair import Keypair
import requests

class PacificaSDK:
    """SDK for placing orders on Pacifica using wallet signing"""

    def __init__(self, private_key: str, base_url: str = "https://api.pacifica.fi/api/v1"):
        """
        Initialize SDK with wallet private key

        Args:
            private_key: Base58 encoded Solana private key
            base_url: Pacifica API base URL
        """
        self.keypair = Keypair.from_base58_string(private_key)
        self.public_key = str(self.keypair.pubkey())
        self.base_url = base_url

    def _sort_json_keys(self, value):
        """Sort JSON keys recursively for signature consistency"""
        if isinstance(value, dict):
            sorted_dict = {}
            for key in sorted(value.keys()):
                sorted_dict[key] = self._sort_json_keys(value[key])
            return sorted_dict
        elif isinstance(value, list):
            return [self._sort_json_keys(item) for item in value]
        else:
            return value

    def _prepare_message(self, header: Dict, payload: Dict) -> str:
        """Prepare message for signing"""
        if "type" not in header or "timestamp" not in header or "expiry_window" not in header:
            raise ValueError("Header must have type, timestamp, and expiry_window")

        data = {
            **header,
            "data": payload,
        }

        message = self._sort_json_keys(data)
        # Compact JSON is required
        message = json.dumps(message, separators=(",", ":"))
        return message

    def _sign_message(self, header: Dict, payload: Dict) -> tuple:
        """Sign a message with the wallet keypair"""
        message = self._prepare_message(header, payload)
        message_bytes = message.encode("utf-8")
        signature = self.keypair.sign_message(message_bytes)
        return (message, base58.b58encode(bytes(signature)).decode("ascii"))

    def create_market_order(
        self,
        symbol: str,
        side: str,  # "bid" for buy, "ask" for sell
        amount: str,  # Amount as string (e.g., "0.1")
        slippage_percent: str = "0.5",
        reduce_only: bool = False,
        client_order_id: Optional[str] = None
    ) -> Dict:
        """
        Create a market order

        Args:
            symbol: Trading symbol (e.g., "BTC", "SOL", "ETH")
            side: "bid" for buy/long, "ask" for sell/short
            amount: Amount to trade as string
            slippage_percent: Max slippage tolerance
            reduce_only: Only reduce existing position
            client_order_id: Optional custom order ID

        Returns:
            API response dict
        """
        # Scaffold the signature header
        timestamp = int(time.time() * 1_000)

        signature_header = {
            "timestamp": timestamp,
            "expiry_window": 5_000,  # 5 second expiry
            "type": "create_market_order",
        }

        # Construct the signature payload
        signature_payload = {
            "symbol": symbol,
            "reduce_only": reduce_only,
            "amount": amount,
            "side": side,
            "slippage_percent": slippage_percent,
            "client_order_id": client_order_id or str(uuid.uuid4()),
        }

        # Sign the message
        message, signature = self._sign_message(signature_header, signature_payload)

        # Construct the request
        request_header = {
            "account": self.public_key,
            "signature": signature,
            "timestamp": signature_header["timestamp"],
            "expiry_window": signature_header["expiry_window"],
        }

        headers = {"Content-Type": "application/json"}

        request = {
            **request_header,
            **signature_payload,
        }

        # Send the request
        url = f"{self.base_url}/orders/create_market"
        response = requests.post(url, json=request, headers=headers)

        # Parse response
        try:
            return response.json()
        except:
            return {
                "status_code": response.status_code,
                "text": response.text,
                "success": False
            }

    def get_account_address(self) -> str:
        """Get the account's public address"""
        return self.public_key
