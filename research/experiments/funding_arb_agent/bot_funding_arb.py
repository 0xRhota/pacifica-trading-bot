#!/usr/bin/env python3
"""
Delta-Neutral Funding Rate Arbitrage Bot
=========================================
Exploits funding rate differentials between Hibachi and Extended DEX
while maintaining delta-neutral exposure.

REQUIRES: Python 3.11+ (for Extended SDK)

Usage:
    # Dry run (default - no real trades)
    python3.11 -m funding_arb_agent.bot_funding_arb --dry-run

    # Live trading
    python3.11 -m funding_arb_agent.bot_funding_arb --live

    # Single cycle test
    python3.11 -m funding_arb_agent.bot_funding_arb --dry-run --once

    # High volume preset
    python3.11 -m funding_arb_agent.bot_funding_arb --live --preset high-volume

    # Custom configuration
    python3.11 -m funding_arb_agent.bot_funding_arb --live --size 200 --interval 600 --rotation 1800

Strategy:
    1. Monitor funding rates on Hibachi and Extended every 15 minutes
    2. When spread > threshold: SHORT high-rate exchange, LONG low-rate exchange
    3. Rotate positions every 1 hour to generate volume
    4. Collect funding rate differential every 8 hours

Volume Generation:
    With default settings ($100 positions, 1 hour rotation):
    - 24 rotations/day * 4 trades * $100 = $9,600/day per symbol
    - 3 symbols = ~$28,800 daily volume

Required Environment Variables:
    HIBACHI_PUBLIC_KEY, HIBACHI_PRIVATE_KEY, HIBACHI_ACCOUNT_ID
    EXTENDED_API_KEY, EXTENDED_STARK_PRIVATE_KEY, EXTENDED_STARK_PUBLIC_KEY, EXTENDED_VAULT
"""

import os
import sys
import asyncio
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

from funding_arb_agent.exchanges.hibachi_adapter import HibachiAdapter
from funding_arb_agent.exchanges.extended_adapter import ExtendedAdapter
from funding_arb_agent.core.arbitrage_engine import FundingArbitrageEngine
from funding_arb_agent.core.config import ArbConfig

# Configure logging
def setup_logging(log_file: str = "logs/funding_arb.log", level: str = "INFO"):
    """Set up logging configuration"""
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

    # Suppress noisy loggers
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Delta-Neutral Funding Rate Arbitrage Bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s --dry-run                    # Test mode (no real trades)
    %(prog)s --live                       # Live trading with defaults
    %(prog)s --live --preset high-volume  # High volume preset
    %(prog)s --live --size 200            # $200 per position
    %(prog)s --dry-run --once             # Single cycle test
        """
    )

    # Mode
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--dry-run', action='store_true', default=True,
                           help='Simulate trades without execution (default)')
    mode_group.add_argument('--live', action='store_true',
                           help='Execute real trades')

    # Presets
    parser.add_argument('--preset', choices=['default', 'high-volume', 'conservative', 'testing'],
                       default='default', help='Configuration preset')

    # Custom config
    parser.add_argument('--size', type=float, help='Position size per leg in USD')
    parser.add_argument('--interval', type=int, help='Scan interval in seconds')
    parser.add_argument('--rotation', type=int, help='Rotation interval in seconds')
    parser.add_argument('--min-spread', type=float, help='Minimum spread threshold (%%)')
    parser.add_argument('--no-rotation', action='store_true', help='Disable position rotation')

    # Symbols
    parser.add_argument('--symbols', nargs='+', default=['BTC', 'ETH', 'SOL'],
                       help='Symbols to trade (default: BTC ETH SOL)')

    # Execution
    parser.add_argument('--once', action='store_true', help='Run single cycle and exit')

    # Logging
    parser.add_argument('--log-file', default='logs/funding_arb.log', help='Log file path')
    parser.add_argument('--log-level', default='INFO', help='Log level')

    return parser.parse_args()


def create_config(args) -> ArbConfig:
    """Create configuration from args"""

    # Start with preset
    if args.preset == 'high-volume':
        config = ArbConfig.high_volume()
    elif args.preset == 'conservative':
        config = ArbConfig.conservative()
    elif args.preset == 'testing':
        config = ArbConfig.testing()
    else:
        config = ArbConfig()

    # Override with command line args
    if args.size:
        config.position_size_usd = args.size
    if args.interval:
        config.scan_interval = args.interval
    if args.rotation:
        config.rotation_interval = args.rotation
    if args.min_spread:
        config.min_spread_threshold = args.min_spread
    if args.no_rotation:
        config.enable_rotation = False
    if args.symbols:
        config.symbols = args.symbols

    # Set mode
    config.dry_run = not args.live

    return config


async def main():
    """Main entry point"""
    args = parse_args()

    # Setup logging
    setup_logging(args.log_file, args.log_level)
    logger = logging.getLogger(__name__)

    # Print banner
    logger.info("")
    logger.info("=" * 70)
    logger.info(" DELTA-NEUTRAL FUNDING RATE ARBITRAGE BOT")
    logger.info("=" * 70)
    logger.info(f" Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f" Mode: {'DRY RUN' if not args.live else 'LIVE TRADING'}")
    logger.info(f" Preset: {args.preset}")
    logger.info("=" * 70)
    logger.info("")

    # Create config
    config = create_config(args)
    config.log_file = args.log_file

    # Create exchange adapters
    hibachi = HibachiAdapter()
    extended = ExtendedAdapter()

    # Create engine
    engine = FundingArbitrageEngine(hibachi, extended, config)

    # Run
    if args.once:
        await engine.run_once()
    else:
        await engine.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        raise
