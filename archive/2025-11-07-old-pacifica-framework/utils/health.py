#!/usr/bin/env python3
"""
DEX Health Check System
Tests connections to all enabled DEXes before trading starts
"""

import os
import asyncio
from typing import Dict, List, Tuple
from dotenv import load_dotenv

load_dotenv()


class DEXHealthCheck:
    """Health checker for DEX connections"""

    @staticmethod
    def mask_key(key: str, show_chars: int = 8) -> str:
        """Safely mask a key for display"""
        if not key or len(key) < show_chars * 2:
            return "***"
        return f"{key[:show_chars]}...{key[-show_chars:]}"

    @staticmethod
    async def check_pacifica() -> Tuple[bool, str]:
        """
        Check Pacifica DEX connection
        Returns: (success: bool, message: str)
        """
        try:
            # Check if Pacifica is configured
            api_key = os.getenv("PACIFICA_API_KEY")
            base_url = os.getenv("PACIFICA_BASE_URL")
            account_address = os.getenv("PACIFICA_ACCOUNT_ADDRESS")

            if not api_key or not base_url or not account_address:
                return False, "Missing Pacifica configuration"

            # TODO: Add actual Pacifica API test when implemented
            # For now, just verify config exists
            masked_key = DEXHealthCheck.mask_key(api_key)
            return True, f"✅ Pacifica configured (key: {masked_key})"

        except Exception as e:
            return False, f"Pacifica error: {e}"

    @staticmethod
    async def check_lighter() -> Tuple[bool, str]:
        """
        Check Lighter DEX connection
        Returns: (success: bool, message: str)
        """
        try:
            import lighter

            api_key_private = os.getenv("LIGHTER_API_KEY_PRIVATE")
            account_index = int(os.getenv("LIGHTER_ACCOUNT_INDEX", "0"))
            api_key_index = int(os.getenv("LIGHTER_API_KEY_INDEX", "3"))

            if not api_key_private:
                return False, "Missing LIGHTER_API_KEY_PRIVATE"

            # Test connection
            BASE_URL = "https://mainnet.zklighter.elliot.ai"
            client = lighter.SignerClient(
                url=BASE_URL,
                private_key=api_key_private,
                account_index=account_index,
                api_key_index=api_key_index,
            )

            err = client.check_client()
            await client.close()

            if err:
                return False, f"Lighter connection failed: {err}"

            masked_key = DEXHealthCheck.mask_key(api_key_private)
            return True, f"✅ Lighter connected (account: #{account_index}, key: {masked_key})"

        except ImportError:
            return False, "Lighter SDK not installed"
        except Exception as e:
            return False, f"Lighter error: {e}"

    @staticmethod
    async def check_all_dexes() -> Dict[str, Tuple[bool, str]]:
        """
        Check all configured DEXes
        Returns: Dict of {dex_name: (success, message)}
        """
        results = {}

        # Check which DEXes are enabled (have required env vars)
        if os.getenv("PACIFICA_API_KEY"):
            results["pacifica"] = await DEXHealthCheck.check_pacifica()

        if os.getenv("LIGHTER_API_KEY_PRIVATE"):
            results["lighter"] = await DEXHealthCheck.check_lighter()

        return results

    @staticmethod
    async def verify_startup() -> bool:
        """
        Verify all enabled DEXes are healthy before starting bot
        Returns: True if all enabled DEXes are healthy, False otherwise
        """
        print("=" * 60)
        print("DEX HEALTH CHECK")
        print("=" * 60)
        print()

        results = await DEXHealthCheck.check_all_dexes()

        if not results:
            print("❌ No DEXes configured")
            print("   Add PACIFICA_API_KEY or LIGHTER_API_KEY_PRIVATE to .env")
            return False

        all_healthy = True
        for dex_name, (success, message) in results.items():
            status = "✅" if success else "❌"
            print(f"{status} {dex_name.upper()}: {message}")
            if not success:
                all_healthy = False

        print()
        if all_healthy:
            print("✅ All DEXes healthy - ready to trade")
        else:
            print("❌ Some DEXes failed - fix issues before trading")

        print("=" * 60)
        return all_healthy


async def main():
    """Run health checks"""
    success = await DEXHealthCheck.verify_startup()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
