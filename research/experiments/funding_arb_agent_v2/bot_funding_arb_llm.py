"""
LLM-Driven Delta-Neutral Funding Rate Arbitrage Bot (v2 - Churn Mode)
=====================================================================
A single LLM makes coordinated trading decisions across Hibachi and Extended
exchanges, while code enforces delta-neutral constraints.

NEW in v2 (Churn Mode):
- Multi-asset: Trade multiple delta-neutral pairs simultaneously
- Churn: Close/reopen positions each cycle to generate volume
- Funding protection: Don't churn near funding times to capture payments

Architecture:
- DataAggregator: Fetches funding rates, volatility, positions from both exchanges
- PromptFormatter: Formats data into structured LLM prompt
- ResponseParser: Parses LLM JSON responses into decisions
- DeltaNeutralExecutor: Executes trades with strict constraints

LLM Decides:
- Which asset(s) to trade (BTC, ETH, SOL)
- When to OPEN, CLOSE, ROTATE, or HOLD
- Entry/exit timing based on spread conditions

Code Enforces (cannot be overridden):
- Equal position sizes on both exchanges
- Opposite directions (one LONG, one SHORT)
- Circuit breakers (volatility, spread collapse, balance)
- Atomic execution with rollback
- Funding time protection (no churn near funding snapshots)
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from funding_arb_agent_v2.core.config import LLMFundingArbConfig
from funding_arb_agent_v2.core.data_aggregator import DataAggregator, AggregatedData
from funding_arb_agent_v2.core.prompt_formatter import PromptFormatter
from funding_arb_agent_v2.core.response_parser import ResponseParser, ArbDecision
from funding_arb_agent_v2.core.executor import DeltaNeutralExecutor

# Setup logging
def setup_logging(config: LLMFundingArbConfig):
    """Configure logging for the bot"""
    log_dir = Path(config.log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        handlers=[
            logging.FileHandler(config.log_file),
            logging.StreamHandler()
        ]
    )

logger = logging.getLogger(__name__)


class LLMFundingArbBot:
    """
    LLM-Driven Delta-Neutral Funding Arbitrage Bot (v2 - Churn Mode)

    One LLM makes coordinated decisions for both exchanges.
    Code strictly enforces delta-neutral constraints.

    v2 Features:
    - Multi-asset positions
    - Churn mode for volume farming
    - Funding time protection
    """

    def __init__(self, config: LLMFundingArbConfig):
        self.config = config
        self.data_aggregator = DataAggregator(config)
        self.prompt_formatter = PromptFormatter(config)
        self.response_parser = ResponseParser(config)
        self.executor = DeltaNeutralExecutor(config)

        self._running = False
        self._cycle_count = 0

    def _is_near_funding_time(self) -> bool:
        """Check if we're within protection window of a funding time"""
        now = datetime.now(timezone.utc)
        protection_minutes = self.config.funding_protection_minutes

        for funding_hour in self.config.funding_times_utc:
            # Check if current time is within X minutes of funding hour
            funding_minute = funding_hour * 60  # Convert to minutes from midnight
            current_minute = now.hour * 60 + now.minute

            # Distance to funding time (handle wrap-around at midnight)
            diff = abs(current_minute - funding_minute)
            if diff > 720:  # More than 12 hours, check the other way
                diff = 1440 - diff

            if diff <= protection_minutes:
                return True

        return False

    def _get_minutes_to_funding(self) -> int:
        """Get minutes until next funding time"""
        now = datetime.now(timezone.utc)
        current_minute = now.hour * 60 + now.minute

        min_diff = 1440  # Start with max (24 hours)
        for funding_hour in self.config.funding_times_utc:
            funding_minute = funding_hour * 60
            diff = funding_minute - current_minute
            if diff < 0:
                diff += 1440  # Next day
            if diff < min_diff:
                min_diff = diff

        return min_diff

    async def initialize(self) -> bool:
        """Initialize all components"""
        logger.info("=" * 60)
        logger.info("LLM FUNDING ARB BOT - INITIALIZATION")
        logger.info("=" * 60)
        logger.info(f"Mode: {'DRY RUN' if self.config.dry_run else 'LIVE TRADING'}")
        logger.info(f"Model: {self.config.model}")
        logger.info(f"Max position per leg: ${self.config.max_position_usd}")
        logger.info(f"Min spread annualized: {self.config.min_spread_annualized}%")
        logger.info(f"Symbols: {', '.join(self.config.symbols)}")
        logger.info("=" * 60)

        # Initialize data aggregator
        if not await self.data_aggregator.initialize():
            logger.error("Failed to initialize data aggregator")
            return False

        # Initialize executor
        if not await self.executor.initialize():
            logger.error("Failed to initialize executor")
            return False

        logger.info("All components initialized successfully")

        # Run startup test
        if not await self._startup_test():
            logger.error("Startup test FAILED - bot will not start")
            return False

        return True

    async def _startup_test(self) -> bool:
        """
        Run startup connectivity and data test.
        Verifies both exchanges are reachable and returning valid data.
        """
        logger.info("")
        logger.info("=" * 60)
        logger.info("STARTUP TEST - Verifying exchange connectivity")
        logger.info("=" * 60)

        try:
            # Test 1: Fetch data from both exchanges
            logger.info("[TEST 1] Fetching data from both exchanges...")
            data = await self.data_aggregator.aggregate()

            if not data:
                logger.error("[FAIL] Could not aggregate data from exchanges")
                return False
            logger.info("[PASS] Data aggregation successful")

            # Test 2: Verify funding rates are available
            logger.info("[TEST 2] Checking funding rate data...")
            if not data.funding or len(data.funding) == 0:
                logger.error("[FAIL] No funding rate data available")
                return False

            for symbol, rates in data.funding.items():
                h = rates.get("Hibachi")
                e = rates.get("Extended")
                if h:
                    logger.info(f"  {symbol} Hibachi: {h.rate:+.6f} (ann: {h.annualized:+.2f}%)")
                if e:
                    logger.info(f"  {symbol} Extended: {e.rate:+.6f} (ann: {e.annualized:+.2f}%)")
            logger.info("[PASS] Funding rates retrieved")

            # Test 3: Verify spreads calculated
            logger.info("[TEST 3] Checking spread calculations...")
            if not data.spreads:
                logger.error("[FAIL] No spread data calculated")
                return False

            best_spread = max(data.spreads.values(), key=lambda s: s.annualized_spread)
            logger.info(f"  Best opportunity: {best_spread.symbol} @ {best_spread.annualized_spread:.2f}% annualized")
            logger.info(f"  Strategy: SHORT {best_spread.short_exchange}, LONG {best_spread.long_exchange}")
            logger.info("[PASS] Spreads calculated")

            # Test 4: Verify account balances
            logger.info("[TEST 4] Checking account balances...")
            logger.info(f"  Hibachi balance:  ${data.hibachi_balance:.2f}")
            logger.info(f"  Extended balance: ${data.extended_balance:.2f}")
            logger.info(f"  Max position/leg: ${data.max_position_size:.2f}")

            if data.max_position_size < self.config.min_position_usd:
                logger.warning(f"[WARN] Max position ${data.max_position_size:.2f} below minimum ${self.config.min_position_usd}")
            else:
                logger.info("[PASS] Balances sufficient")

            # Test 5: Test LLM connectivity
            logger.info("[TEST 5] Testing LLM API connectivity...")
            test_response = await self._query_llm("Reply with exactly: OK")
            if test_response and "OK" in test_response.upper():
                logger.info("[PASS] LLM API responsive")
            else:
                logger.warning("[WARN] LLM API test returned unexpected response")
                # Not a fatal error - might still work

            # Test 6: Check for existing positions
            logger.info("[TEST 6] Checking existing positions...")
            if data.positions:
                logger.info(f"  Found {len(data.positions)} existing position(s):")
                for pos in data.positions:
                    logger.info(f"    {pos.exchange} {pos.symbol}: {pos.side} ${pos.notional:.2f}")
            else:
                logger.info("  No existing positions")
            logger.info("[PASS] Position check complete")

            logger.info("")
            logger.info("=" * 60)
            logger.info("STARTUP TEST PASSED - All systems operational")
            logger.info("=" * 60)
            logger.info("")

            return True

        except Exception as e:
            logger.error(f"[FAIL] Startup test error: {e}", exc_info=True)
            return False

    async def run(self):
        """Main bot loop"""
        self._running = True
        logger.info(f"Starting main loop (interval: {self.config.scan_interval}s)")

        while self._running:
            try:
                await self._run_cycle()
            except Exception as e:
                logger.error(f"Error in cycle: {e}", exc_info=True)

            # Wait for next cycle
            await asyncio.sleep(self.config.scan_interval)

    async def _run_cycle(self):
        """Run one decision cycle"""
        self._cycle_count += 1
        cycle_start = datetime.now(timezone.utc)

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"CYCLE {self._cycle_count} - {cycle_start.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        if self.config.churn_mode:
            logger.info(f"MODE: CHURN (volume farming)")
        if self.config.multi_asset:
            logger.info(f"MODE: MULTI-ASSET")
        logger.info("=" * 60)

        # Step 1: Check funding time protection
        near_funding = self._is_near_funding_time()
        minutes_to_funding = self._get_minutes_to_funding()
        if near_funding:
            logger.info(f"⏰ FUNDING PROTECTION: Within {self.config.funding_protection_minutes}min of funding time")
            logger.info(f"   Next funding in {minutes_to_funding} minutes - HOLDING positions")

        # Step 2: Aggregate data from both exchanges
        logger.info("Step 1: Fetching data from exchanges...")
        data = await self.data_aggregator.aggregate()

        if not data:
            logger.error("Failed to aggregate data")
            return

        # Log summary
        self._log_data_summary(data)

        # ===== CHURN MODE LOGIC =====
        if self.config.churn_mode and data.positions and not near_funding:
            logger.info("")
            logger.info("🔄 CHURN MODE: Closing existing positions to generate volume...")
            await self._churn_close_all(data)
            # After closing, we'll reopen in the normal flow below

        # Step 3: Get viable opportunities (above min spread)
        viable_assets = []
        for symbol, spread in data.spreads.items():
            if spread.annualized_spread >= self.config.min_spread_annualized:
                vol = data.volatility.get(symbol)
                if vol and vol.is_safe:
                    viable_assets.append((symbol, spread))

        # Sort by spread (best first)
        viable_assets.sort(key=lambda x: x[1].annualized_spread, reverse=True)

        if viable_assets:
            logger.info(f"Viable opportunities: {[a[0] for a in viable_assets]}")
        else:
            logger.info("No viable opportunities above threshold")

        # ===== MULTI-ASSET MODE =====
        if self.config.multi_asset and len(viable_assets) > 1:
            logger.info("")
            logger.info("📊 MULTI-ASSET MODE: Opening positions on all viable assets...")
            await self._open_multi_asset(viable_assets, data)
        else:
            # Standard single-asset flow with LLM
            await self._run_single_asset_cycle(data)

        cycle_time = (datetime.now(timezone.utc) - cycle_start).total_seconds()
        logger.info(f"Cycle completed in {cycle_time:.2f}s")

    async def _churn_close_all(self, data: AggregatedData):
        """Close all existing positions for churn (volume generation)"""
        closed_assets = set()
        for pos in data.positions:
            if pos.symbol not in closed_assets:
                logger.info(f"  Closing {pos.symbol} position...")
                close_decision = ArbDecision(
                    action="CLOSE",
                    asset=pos.symbol,
                    hibachi_direction=None,
                    extended_direction=None,
                    reasoning="Churn - closing for volume generation",
                    confidence=1.0,
                    raw_response=""
                )
                result = await self.executor.execute(close_decision, data)
                if result.success:
                    logger.info(f"  ✅ Closed {pos.symbol}")
                    closed_assets.add(pos.symbol)
                else:
                    logger.warning(f"  ❌ Failed to close {pos.symbol}: {result.error}")

        # Small delay to let orders settle
        if closed_assets:
            await asyncio.sleep(2)

    async def _open_multi_asset(self, viable_assets: list, data: AggregatedData):
        """Open delta-neutral positions on multiple assets"""
        # Use FULL position size per asset (leverage allows multiple positions)
        # Don't divide by num_assets - we want maximum volume per asset
        num_assets = len(viable_assets)
        per_asset_size = min(
            data.max_position_size,  # Full balance per asset
            self.config.max_position_usd
        )

        logger.info(f"  Opening {num_assets} positions @ ${per_asset_size:.2f} each (FULL SIZE)")

        for symbol, spread in viable_assets:
            logger.info(f"  Opening {symbol} ({spread.annualized_spread:.2f}% spread)...")

            # Determine directions based on spread
            open_decision = ArbDecision(
                action="OPEN",
                asset=symbol,
                hibachi_direction="SHORT" if spread.short_exchange == "Hibachi" else "LONG",
                extended_direction="SHORT" if spread.short_exchange == "Extended" else "LONG",
                reasoning=f"Multi-asset: {symbol} has {spread.annualized_spread:.2f}% annualized spread",
                confidence=0.9,
                raw_response=""
            )

            # Temporarily adjust max position for this trade
            original_max = self.config.max_position_usd
            self.config.max_position_usd = per_asset_size

            result = await self.executor.execute(open_decision, data)

            self.config.max_position_usd = original_max

            if result.success:
                logger.info(f"  ✅ Opened {symbol}: H={result.hibachi_order_id}, E={result.extended_order_id}")
            else:
                logger.warning(f"  ❌ Failed to open {symbol}: {result.error}")

            # Small delay between orders
            await asyncio.sleep(1)

    async def _run_single_asset_cycle(self, data: AggregatedData):
        """Standard single-asset cycle with LLM decision"""
        # Step 2: Format prompt for LLM
        logger.info("Step 2: Formatting prompt for LLM...")
        prompt = self.prompt_formatter.format_decision_prompt(data)

        # Step 3: Query LLM for decision
        logger.info("Step 3: Querying LLM for decision...")
        llm_response = await self._query_llm(prompt)

        if not llm_response:
            logger.error("Failed to get LLM response")
            return

        # Step 4: Parse LLM response
        logger.info("Step 4: Parsing LLM response...")
        decision = self.response_parser.parse(llm_response)

        if not decision:
            logger.warning("Failed to parse LLM response")
            return

        logger.info(f"LLM Decision: {decision.action}")
        if decision.asset:
            logger.info(f"  Asset: {decision.asset}")
            logger.info(f"  Hibachi: {decision.hibachi_direction}")
            logger.info(f"  Extended: {decision.extended_direction}")
        logger.info(f"  Confidence: {decision.confidence:.2f}")
        logger.info(f"  Reasoning: {decision.reasoning[:200]}...")

        # Step 5: Validate decision against data
        if not self.response_parser.validate_against_data(decision, data):
            logger.warning("Decision failed validation against market data")
            return

        # Step 6: Execute decision
        logger.info("Step 5: Executing decision...")
        result = await self.executor.execute(decision, data)

        # Log result
        if result.success:
            logger.info(f"Execution SUCCESS: {result.action}")
            if result.position_size > 0:
                logger.info(f"  Position size: ${result.position_size:.2f} per leg")
            if result.hibachi_order_id:
                logger.info(f"  Hibachi order: {result.hibachi_order_id}")
            if result.extended_order_id:
                logger.info(f"  Extended order: {result.extended_order_id}")
        else:
            logger.warning(f"Execution FAILED: {result.error}")
            if result.rolled_back:
                logger.warning("  Trade was rolled back")

    def _log_data_summary(self, data):
        """Log a summary of aggregated data"""
        logger.info("")
        logger.info("--- DATA SUMMARY ---")

        # Funding rates
        logger.info("Funding Rates:")
        for symbol, rates in data.funding.items():
            h = rates.get("Hibachi")
            e = rates.get("Extended")
            h_str = f"{h.rate:+.6f}" if h else "N/A"
            e_str = f"{e.rate:+.6f}" if e else "N/A"
            logger.info(f"  {symbol}: Hibachi {h_str} | Extended {e_str}")

        # Spreads
        logger.info("Spreads (best to worst):")
        sorted_spreads = sorted(
            data.spreads.items(),
            key=lambda x: x[1].annualized_spread,
            reverse=True
        )
        for symbol, spread in sorted_spreads:
            logger.info(
                f"  {symbol}: {spread.annualized_spread:.2f}% annualized | "
                f"SHORT {spread.short_exchange}, LONG {spread.long_exchange}"
            )

        # Volatility
        logger.info("Volatility:")
        for symbol, vol in data.volatility.items():
            if vol:
                status = "SAFE" if vol.is_safe else "HIGH"
                logger.info(f"  {symbol}: {vol.volatility_1h:.2f}% 1h | {status}")

        # Positions
        if data.positions:
            logger.info("Current Positions:")
            for pos in data.positions:
                logger.info(f"  {pos.exchange} {pos.symbol}: {pos.side} ${pos.notional:.2f}")
        else:
            logger.info("Positions: None")

        # Balances
        logger.info(f"Balances: Hibachi ${data.hibachi_balance:.2f} | Extended ${data.extended_balance:.2f}")
        logger.info(f"Max position per leg: ${data.max_position_size:.2f}")

        if data.hours_until_funding is not None:
            logger.info(f"Next funding in: {data.hours_until_funding:.1f}h")

        logger.info("-------------------")
        logger.info("")

    async def _query_llm(self, prompt: str) -> str:
        """Query the LLM for a decision"""
        try:
            # Use OpenRouter to access Qwen-max
            import httpx

            openrouter_key = os.getenv('OPEN_ROUTER') or os.getenv('OPENROUTER_API_KEY')
            if openrouter_key:
                openrouter_key = openrouter_key.strip().strip('"')

            if not openrouter_key:
                logger.error("No OpenRouter API key found (OPEN_ROUTER or OPENROUTER_API_KEY)")
                return None

            # Map model name to OpenRouter model ID
            model_map = {
                "qwen-max": "qwen/qwen-max",
                "deepseek-chat": "deepseek/deepseek-chat",
                "claude-3-sonnet": "anthropic/claude-3-sonnet",
            }

            model_id = model_map.get(self.config.model, self.config.model)

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {openrouter_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model_id,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": self.config.temperature,
                        "max_tokens": self.config.max_tokens,
                    }
                )

                if response.status_code != 200:
                    logger.error(f"LLM API error: {response.status_code} - {response.text}")
                    return None

                result = response.json()
                return result["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error(f"Error querying LLM: {e}", exc_info=True)
            return None

    def stop(self):
        """Stop the bot"""
        logger.info("Stopping bot...")
        self._running = False


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="LLM-Driven Delta-Neutral Funding Arbitrage Bot"
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Enable live trading (default: dry run)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Scan interval in seconds (default: 300)"
    )
    parser.add_argument(
        "--max-position",
        type=float,
        default=100.0,
        help="Max position size per leg in USD (default: 100)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="qwen-max",
        choices=["qwen-max", "deepseek-chat"],
        help="LLM model to use (default: qwen-max)"
    )
    parser.add_argument(
        "--preset",
        type=str,
        choices=["testing", "conservative", "churn"],
        help="Use a preset configuration"
    )
    parser.add_argument(
        "--churn",
        action="store_true",
        help="Enable churn mode (close/reopen every cycle for volume)"
    )
    parser.add_argument(
        "--multi-asset",
        action="store_true",
        help="Enable multi-asset mode (multiple simultaneous positions)"
    )

    args = parser.parse_args()

    # Create config
    if args.preset == "testing":
        config = LLMFundingArbConfig.testing()
    elif args.preset == "conservative":
        config = LLMFundingArbConfig.conservative()
    elif args.preset == "churn":
        config = LLMFundingArbConfig.churn()
    else:
        config = LLMFundingArbConfig()

    # Override with command line args
    config.dry_run = not args.live
    config.scan_interval = args.interval
    config.max_position_usd = args.max_position
    config.model = args.model

    # Churn mode flags
    if args.churn:
        config.churn_mode = True
    if args.multi_asset:
        config.multi_asset = True

    # Setup logging
    setup_logging(config)

    # Create and run bot
    bot = LLMFundingArbBot(config)

    if not await bot.initialize():
        logger.error("Bot initialization failed")
        sys.exit(1)

    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
