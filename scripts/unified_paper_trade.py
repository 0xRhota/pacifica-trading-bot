#!/usr/bin/env python3
"""
Unified Paper Trading Test - All Three Exchanges
Tests the shared learning strategy across Hibachi, Extended, and Paradex

Simulates:
- $100 per exchange
- Real market data from all three
- Shared learning between bots
- Sentiment-aware decision making
- 2-hour test duration

Usage: python3.11 scripts/unified_paper_trade.py
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, '.env'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler('logs/unified_paper_trade.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Suppress noisy loggers
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)
logging.getLogger('aiohttp').setLevel(logging.WARNING)

# Import shared components
from llm_agent.data.sentiment_fetcher import SentimentFetcher
from llm_agent.shared_learning import SharedLearning
from llm_agent.llm import LLMTradingAgent


class PaperPosition:
    """Tracks a simulated leveraged position"""
    def __init__(self, symbol: str, side: str, entry_price: float, notional: float,
                 margin: float, leverage: int, entry_time: datetime, exchange: str):
        self.symbol = symbol
        self.side = side  # LONG or SHORT
        self.entry_price = entry_price
        self.notional = notional  # Total position value (e.g., $300)
        self.margin = margin  # Collateral used (e.g., $30 at 10x)
        self.leverage = leverage
        self.entry_time = entry_time
        self.exchange = exchange
        self.current_price = entry_price
        # Calculate position size in base asset
        self.size_in_asset = notional / entry_price  # e.g., 0.0032 BTC

    def update_price(self, price: float):
        self.current_price = price

    def get_pnl(self) -> float:
        """PnL in USD based on notional value"""
        price_change_pct = (self.current_price - self.entry_price) / self.entry_price
        if self.side == 'LONG':
            return self.notional * price_change_pct
        else:  # SHORT
            return self.notional * (-price_change_pct)

    def get_pnl_pct(self) -> float:
        """PnL as percentage of MARGIN (leveraged return)"""
        if self.margin == 0:
            return 0
        return (self.get_pnl() / self.margin) * 100

    def get_price_change_pct(self) -> float:
        """Raw price change percentage"""
        if self.entry_price == 0:
            return 0
        return ((self.current_price - self.entry_price) / self.entry_price) * 100

    def hold_hours(self) -> float:
        return (datetime.now() - self.entry_time).total_seconds() / 3600


class ExchangeSimulator:
    """Simulates trading on a single exchange"""

    def __init__(self, name: str, initial_balance: float = 100.0):
        self.name = name
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions: Dict[str, PaperPosition] = {}
        self.closed_trades: List[Dict] = []
        self.total_volume = 0.0

        # Exit rules (profit-focused)
        self.take_profit_pct = 8.0
        self.stop_loss_pct = 4.0
        self.max_hold_hours = 48.0
        self.cut_loser_hours = 4.0

    def open_position(self, symbol: str, side: str, price: float,
                      notional: float, leverage: int = 10) -> bool:
        """Open a new leveraged paper position"""
        if symbol in self.positions:
            return False

        margin = notional / leverage  # e.g., $300 / 10 = $30 margin

        # Check if we have enough balance
        if margin > self.balance:
            logger.warning(f"  [{self.name}] Insufficient balance for ${notional} position")
            return False

        self.positions[symbol] = PaperPosition(
            symbol=symbol,
            side=side,
            entry_price=price,
            notional=notional,
            margin=margin,
            leverage=leverage,
            entry_time=datetime.now(),
            exchange=self.name
        )
        self.total_volume += notional  # Track notional volume
        self.balance -= margin  # Reserve margin

        logger.info(f"  [{self.name}] OPEN {side} {symbol} @ ${price:,.2f} (${notional:.0f} notional, {leverage}x)")
        return True

    def close_position(self, symbol: str, price: float, reason: str) -> Optional[float]:
        """Close a paper position and return P&L"""
        if symbol not in self.positions:
            return None

        pos = self.positions[symbol]
        pos.update_price(price)
        pnl = pos.get_pnl()
        pnl_pct = pos.get_pnl_pct()

        # Return margin + PnL to balance
        self.balance += pos.margin + pnl
        self.total_volume += pos.notional  # Track close volume

        # Record trade
        self.closed_trades.append({
            'symbol': symbol,
            'side': pos.side,
            'entry_price': pos.entry_price,
            'exit_price': price,
            'notional': pos.notional,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'hold_hours': pos.hold_hours(),
            'reason': reason,
            'timestamp': datetime.now()
        })

        emoji = "✅" if pnl > 0 else "❌"
        logger.info(f"  [{self.name}] {emoji} CLOSE {pos.side} {symbol} @ ${price:,.2f} | P&L: ${pnl:+.2f} ({pnl_pct:+.1f}%) | {reason}")

        del self.positions[symbol]
        return pnl

    def check_exits(self, prices: Dict[str, float]) -> List[Tuple[str, str]]:
        """Check positions for exit conditions, return list of (symbol, reason)"""
        exits = []

        for symbol, pos in list(self.positions.items()):
            if symbol in prices:
                pos.update_price(prices[symbol])
                pnl_pct = pos.get_pnl_pct()
                hold_hours = pos.hold_hours()

                # Take Profit
                if pnl_pct >= self.take_profit_pct:
                    exits.append((symbol, f"TAKE PROFIT: +{pnl_pct:.1f}%"))
                # Stop Loss
                elif pnl_pct <= -self.stop_loss_pct:
                    exits.append((symbol, f"STOP LOSS: {pnl_pct:.1f}%"))
                # Cut loser after 4h
                elif hold_hours >= self.cut_loser_hours and pnl_pct < 0:
                    exits.append((symbol, f"CUT LOSER: {hold_hours:.1f}h underwater"))
                # Max hold
                elif hold_hours >= self.max_hold_hours:
                    exits.append((symbol, f"TIME EXIT: {hold_hours:.1f}h"))

        return exits

    def get_stats(self) -> Dict:
        """Get exchange statistics"""
        wins = len([t for t in self.closed_trades if t['pnl'] > 0])
        losses = len([t for t in self.closed_trades if t['pnl'] <= 0])
        total_pnl = sum(t['pnl'] for t in self.closed_trades)
        unrealized = sum(pos.get_pnl() for pos in self.positions.values())

        return {
            'name': self.name,
            'initial': self.initial_balance,
            'balance': self.balance,
            'total_pnl': total_pnl,
            'unrealized_pnl': unrealized,
            'total_equity': self.balance + unrealized,
            'trades': len(self.closed_trades),
            'wins': wins,
            'losses': losses,
            'win_rate': wins / max(1, wins + losses) * 100,
            'open_positions': len(self.positions),
            'volume': self.total_volume
        }


class UnifiedPaperTrader:
    """Orchestrates paper trading across all exchanges"""

    def __init__(self, duration_hours: float = 2.0, cycle_minutes: int = 10):
        self.duration_hours = duration_hours
        self.cycle_minutes = cycle_minutes
        self.start_time = None

        # Initialize exchanges
        self.hibachi = ExchangeSimulator("Hibachi", 100.0)
        self.extended = ExchangeSimulator("Extended", 100.0)
        self.paradex = ExchangeSimulator("Paradex", 100.0)

        # Shared components
        self.sentiment_fetcher = SentimentFetcher()
        self.shared_learning = SharedLearning(bot_name="orchestrator")

        # LLM agent for decisions
        openrouter_key = os.getenv('OPEN_ROUTER')
        cambrian_key = os.getenv('CAMBRIAN_API_KEY')

        if not openrouter_key:
            raise ValueError("OPEN_ROUTER env var required")

        self.llm_agent = LLMTradingAgent(
            deepseek_api_key=openrouter_key,
            cambrian_api_key=cambrian_key,
            model="qwen-max",
            max_retries=1,
            daily_spend_limit=5.0,
            max_positions=3
        )

        # Data fetchers (will be initialized)
        self.hibachi_sdk = None
        self.extended_client = None
        self.paradex_client = None

        # Position sizing - MATCHES ACTUAL EXTENDED EXECUTOR LOGIC
        # See: extended_agent/execution/extended_executor.py lines 180-210
        # Formula: position_size_usd = account_balance * 0.80 * leverage
        # With $100 balance and 3x leverage: $100 * 0.80 * 3 = $240 notional
        # Clamped to min $100, max $1000
        self.base_leverage = 3.0  # BASE_LEVERAGE from executor
        self.base_pct = 0.80  # base_pct from executor
        self.min_notional = 100.0
        self.max_notional = 1000.0
        self.max_positions_per_exchange = 5

    async def initialize(self):
        """Initialize exchange connections"""
        logger.info("=" * 70)
        logger.info("UNIFIED PAPER TRADING TEST")
        logger.info("=" * 70)
        logger.info(f"Duration: {self.duration_hours} hours")
        logger.info(f"Cycle: {self.cycle_minutes} minutes")
        logger.info(f"Balance: $100 per exchange ($300 total)")
        logger.info(f"Position Sizing: balance × {self.base_pct} × {self.base_leverage}-5x leverage")
        logger.info(f"  → With $100: ${100 * self.base_pct * self.base_leverage:.0f} to ${100 * self.base_pct * 5:.0f} notional")
        logger.info("=" * 70)

        # Initialize Hibachi - using REST API directly (no SDK needed for paper trading)
        logger.info("✅ Hibachi data via REST API (no SDK needed for paper trade)")

        # Initialize Extended
        try:
            from extended_agent.execution.extended_executor import create_extended_executor_from_env
            self.extended_client = create_extended_executor_from_env(
                trade_tracker=None,
                dry_run=True
            )
            if self.extended_client:
                logger.info("✅ Extended connected")
            else:
                logger.warning("⚠️ Extended connection failed")
        except Exception as e:
            logger.error(f"❌ Extended init failed: {e}")

        # Initialize Paradex
        try:
            from paradex_py import ParadexSubkey
            paradex_key = os.getenv('PARADEX_PRIVATE_SUBKEY')

            if paradex_key:
                self.paradex_client = ParadexSubkey(
                    env='prod',
                    l2_private_key=paradex_key,
                    l2_address=os.getenv('PARADEX_ACCOUNT_ADDRESS'),
                )
                logger.info("✅ Paradex connected")
            else:
                logger.warning("⚠️ Paradex credentials missing")
        except Exception as e:
            logger.error(f"❌ Paradex init failed: {e}")

        self.start_time = datetime.now()
        logger.info("=" * 70)

    async def fetch_hibachi_data(self) -> Dict[str, Dict]:
        """Fetch market data from Hibachi via REST API"""
        import aiohttp
        data = {}

        try:
            symbols = ['BTC/USDT-P', 'ETH/USDT-P', 'SOL/USDT-P']
            base_url = "https://data-api.hibachi.xyz"

            async with aiohttp.ClientSession() as session:
                for symbol in symbols:
                    try:
                        url = f"{base_url}/market/data/prices?symbol={symbol}"

                        async with session.get(url, timeout=5) as resp:
                            if resp.status == 200:
                                result = await resp.json()
                                price = result.get('price') or result.get('lastPrice') or result.get('markPrice')
                                if price:
                                    data[symbol] = {
                                        'price': float(price),
                                        'exchange': 'Hibachi'
                                    }
                    except Exception as e:
                        logger.debug(f"Hibachi {symbol} fetch error: {e}")
        except Exception as e:
            logger.warning(f"Hibachi data error: {e}")

        return data

    async def fetch_extended_data(self) -> Dict[str, Dict]:
        """Fetch market data from Extended"""
        data = {}
        if not self.extended_client:
            return data

        try:
            markets = ['BTC-USD', 'ETH-USD', 'SOL-USD']
            for market in markets:
                try:
                    # Use the SDK's market price method
                    price = await self.extended_client._get_market_price(market)
                    if price:
                        data[market] = {
                            'price': float(price),
                            'exchange': 'Extended'
                        }
                except Exception as e:
                    logger.debug(f"Extended {market} error: {e}")
        except Exception as e:
            logger.warning(f"Extended data error: {e}")

        return data

    async def fetch_paradex_data(self) -> Dict[str, Dict]:
        """Fetch market data from Paradex"""
        data = {}
        if not self.paradex_client:
            return data

        try:
            bbo = self.paradex_client.api_client.fetch_bbo(market="BTC-USD-PERP")
            if bbo:
                bid = float(bbo['bid'])
                ask = float(bbo['ask'])
                mid = (bid + ask) / 2
                data['BTC-USD-PERP'] = {
                    'price': mid,
                    'bid': bid,
                    'ask': ask,
                    'spread_bps': (ask - bid) / mid * 10000,
                    'exchange': 'Paradex'
                }
        except Exception as e:
            logger.warning(f"Paradex data error: {e}")

        return data

    async def fetch_all_data(self) -> Dict[str, Dict]:
        """Fetch data from all exchanges"""
        hibachi_data = await self.fetch_hibachi_data()
        extended_data = await self.fetch_extended_data()
        paradex_data = await self.fetch_paradex_data()

        return {
            'hibachi': hibachi_data,
            'extended': extended_data,
            'paradex': paradex_data
        }

    async def get_sentiment(self) -> Dict:
        """Fetch market sentiment"""
        try:
            sentiment = await self.sentiment_fetcher.fetch_all()
            return sentiment
        except Exception as e:
            logger.warning(f"Sentiment fetch error: {e}")
            return {}

    def format_market_summary(self, all_data: Dict) -> str:
        """Format market data for LLM prompt"""
        lines = ["LIVE MARKET DATA (Paper Trading Test):"]
        lines.append("-" * 50)

        # Hibachi
        if all_data.get('hibachi'):
            lines.append("HIBACHI (Low fees, perpetuals):")
            for symbol, info in all_data['hibachi'].items():
                lines.append(f"  {symbol}: ${info['price']:,.2f}")

        # Extended
        if all_data.get('extended'):
            lines.append("EXTENDED (Starknet perps):")
            for symbol, info in all_data['extended'].items():
                lines.append(f"  {symbol}: ${info['price']:,.2f}")

        # Paradex
        if all_data.get('paradex'):
            lines.append("PARADEX (Grid MM target):")
            for symbol, info in all_data['paradex'].items():
                lines.append(f"  {symbol}: ${info['price']:,.2f} (spread: {info.get('spread_bps', 0):.1f} bps)")

        return "\n".join(lines)

    async def make_decisions(self, all_data: Dict, sentiment: Dict) -> List[Dict]:
        """Use LLM to make trading decisions"""
        decisions = []

        # Build prompt
        market_summary = self.format_market_summary(all_data)
        sentiment_context = self.sentiment_fetcher.get_prompt_context(sentiment) if sentiment else ""
        shared_context = self.shared_learning.get_prompt_context()

        # Current positions
        positions_text = "CURRENT POSITIONS:\n"
        for exchange in [self.hibachi, self.extended, self.paradex]:
            for symbol, pos in exchange.positions.items():
                pnl_pct = pos.get_pnl_pct()
                positions_text += f"  [{exchange.name}] {pos.side} {symbol} @ ${pos.entry_price:,.2f} | P&L: {pnl_pct:+.1f}%\n"

        if not any([self.hibachi.positions, self.extended.positions, self.paradex.positions]):
            positions_text += "  (No open positions)\n"

        prompt = f"""You are a trading AI managing positions across THREE exchanges: Hibachi, Extended, and Paradex.

{market_summary}

{positions_text}

{sentiment_context}

{shared_context}

STRATEGY: VOLUME + GAINS ACROSS ALL EXCHANGES
- Target: +8% take profit, -4% stop loss (2:1 R:R)
- Hold time: Up to 48 hours
- Max 3 positions per exchange
- CRITICAL: We want VOLUME through ALL exchanges, not just the cheapest one!

RULES:
1. If you're bullish on BTC, open BTC positions on ALL exchanges that don't have one
2. If you're bullish on ETH, open ETH positions on ALL exchanges that don't have one
3. Price differences between exchanges are IRRELEVANT - we want exposure everywhere
4. Each exchange should have at least 1 position if there's any reasonable setup

TASK: For EACH exchange without a position, recommend a trade.
- Don't just pick the cheapest price - we want volume on ALL platforms
- If bullish on an asset, trade it on EVERY exchange
- Recommend MULTIPLE trades (one per exchange) if opportunities exist

Respond with UP TO 3 trades (one per exchange). Format:
EXCHANGE: [Hibachi/Extended/Paradex]
SYMBOL: [exact symbol from data above]
ACTION: [BUY/SELL]
CONFIDENCE: [0.6-1.0]
REASON: [brief explanation]

---

(Repeat for each exchange that needs a trade)"""

        try:
            # Add explicit instruction to avoid reasoning-only mode
            prompt += "\n\nIMPORTANT: Output your response directly. Do not think internally - output the EXCHANGE/SYMBOL/ACTION/CONFIDENCE/REASON format immediately."

            result = self.llm_agent.model_client.query(
                prompt=prompt,
                max_tokens=800,  # Increased to give room for actual output
                temperature=0.3
            )

            logger.info(f"  LLM result keys: {result.keys() if result else 'None'}")

            if result:
                # Try 'content' or 'text' or direct response
                content = result.get('content') or result.get('text') or str(result)
                if content:
                    logger.info(f"  LLM RAW RESPONSE:\n{content[:800]}...")
                    decisions = self._parse_decisions(content, all_data)
                    logger.info(f"  Parsed {len(decisions)} decisions")
                else:
                    logger.warning(f"  LLM result has no content: {result}")

        except Exception as e:
            logger.error(f"LLM decision error: {e}")
            import traceback
            traceback.print_exc()

        return decisions

    def _parse_decisions(self, content: str, all_data: Dict) -> List[Dict]:
        """Parse LLM response into decisions"""
        decisions = []

        lines = content.strip().split('\n')
        current = {}

        for line in lines:
            line = line.strip()
            if line.startswith('EXCHANGE:'):
                if current.get('action') and current['action'] not in ['HOLD', 'NONE']:
                    decisions.append(current)
                current = {'exchange': line.split(':', 1)[1].strip()}
            elif line.startswith('SYMBOL:'):
                current['symbol'] = line.split(':', 1)[1].strip()
            elif line.startswith('ACTION:'):
                current['action'] = line.split(':', 1)[1].strip().upper()
            elif line.startswith('CONFIDENCE:'):
                try:
                    current['confidence'] = float(line.split(':', 1)[1].strip())
                except:
                    current['confidence'] = 0.5
            elif line.startswith('REASON:'):
                current['reason'] = line.split(':', 1)[1].strip()

        if current.get('action') and current['action'] not in ['HOLD', 'NONE']:
            decisions.append(current)

        # Filter low confidence (lowered from 0.7 to 0.6 for more activity)
        decisions = [d for d in decisions if d.get('confidence', 0) >= 0.6]

        return decisions

    async def execute_cycle(self, all_data: Dict):
        """Execute one trading cycle"""

        # Check exits first
        hibachi_prices = {s: d['price'] for s, d in all_data.get('hibachi', {}).items()}
        extended_prices = {s: d['price'] for s, d in all_data.get('extended', {}).items()}
        paradex_prices = {s: d['price'] for s, d in all_data.get('paradex', {}).items()}

        # Process exits
        for symbol, reason in self.hibachi.check_exits(hibachi_prices):
            if symbol in hibachi_prices:
                self.hibachi.close_position(symbol, hibachi_prices[symbol], reason)

        for symbol, reason in self.extended.check_exits(extended_prices):
            if symbol in extended_prices:
                self.extended.close_position(symbol, extended_prices[symbol], reason)

        for symbol, reason in self.paradex.check_exits(paradex_prices):
            if symbol in paradex_prices:
                self.paradex.close_position(symbol, paradex_prices[symbol], reason)

        # Get sentiment
        sentiment = await self.get_sentiment()

        # Make decisions
        decisions = await self.make_decisions(all_data, sentiment)

        # Execute decisions
        for decision in decisions:
            exchange_name = decision.get('exchange', '').lower()
            symbol = decision.get('symbol')
            action = decision.get('action')
            reason = decision.get('reason', '')
            confidence = decision.get('confidence', 0)

            if not exchange_name or not symbol or not action:
                continue

            # Map to correct exchange
            if 'hibachi' in exchange_name:
                exchange = self.hibachi
                prices = hibachi_prices
            elif 'extended' in exchange_name:
                exchange = self.extended
                prices = extended_prices
            elif 'paradex' in exchange_name:
                exchange = self.paradex
                prices = paradex_prices
            else:
                continue

            # Check if we can trade
            if len(exchange.positions) >= self.max_positions_per_exchange:
                logger.info(f"  [{exchange.name}] Skip: max positions reached")
                continue

            if symbol in exchange.positions:
                logger.info(f"  [{exchange.name}] Skip: already have {symbol}")
                continue

            # Check shared learning for blocks
            base_symbol = symbol.split('/')[0].split('-')[0]  # Extract BTC, ETH, etc
            direction = 'LONG' if action == 'BUY' else 'SHORT'

            is_blocked, block_reason = self.shared_learning.is_blocked(base_symbol, direction)
            if is_blocked:
                logger.info(f"  [{exchange.name}] BLOCKED: {block_reason}")
                continue

            # Get price
            price = prices.get(symbol)
            if not price:
                continue

            # Calculate dynamic position size (matches Extended executor logic)
            # Formula: position_size_usd = balance * base_pct * leverage
            # Leverage scales with confidence: 3x (low) to 5x (high)
            if confidence < 0.5:
                leverage = self.base_leverage
            elif confidence < 0.7:
                leverage = self.base_leverage + 0.5
            elif confidence < 0.85:
                leverage = self.base_leverage + 1.0
            else:
                leverage = 5.0  # MAX_LEVERAGE

            position_notional = exchange.balance * self.base_pct * leverage
            position_notional = max(self.min_notional, min(position_notional, self.max_notional))

            # Execute
            side = 'LONG' if action == 'BUY' else 'SHORT'
            logger.info(f"  LLM Decision: {action} {symbol} on {exchange.name} (conf: {confidence:.2f})")
            logger.info(f"    Sizing: ${exchange.balance:.0f} × {self.base_pct} × {leverage:.1f}x = ${position_notional:.0f} notional")
            logger.info(f"    Reason: {reason[:80]}...")

            exchange.open_position(symbol, side, price, position_notional, int(leverage))

            # Record in shared learning
            self.shared_learning.register_position(base_symbol, direction, "orchestrator")

    def print_status(self, cycle: int, all_data: Dict):
        """Print current status"""
        elapsed = (datetime.now() - self.start_time).total_seconds() / 60

        logger.info("")
        logger.info("=" * 70)
        logger.info(f"CYCLE {cycle} | {elapsed:.0f} min elapsed")
        logger.info("=" * 70)

        # Market prices
        logger.info("PRICES:")
        for exchange_name, data in all_data.items():
            for symbol, info in data.items():
                logger.info(f"  [{exchange_name}] {symbol}: ${info['price']:,.2f}")

        # Exchange summaries
        logger.info("")
        logger.info("EXCHANGE STATUS:")
        for exchange in [self.hibachi, self.extended, self.paradex]:
            stats = exchange.get_stats()
            logger.info(f"  [{exchange.name}] Balance: ${stats['balance']:.2f} | "
                       f"Unrealized: ${stats['unrealized_pnl']:+.2f} | "
                       f"Trades: {stats['trades']} | "
                       f"Open: {stats['open_positions']}")

            # Show open positions
            for symbol, pos in exchange.positions.items():
                pnl_pct = pos.get_pnl_pct()
                logger.info(f"       {pos.side} {symbol}: {pnl_pct:+.1f}% ({pos.hold_hours():.1f}h)")

    def print_final_report(self):
        """Print final trading report"""
        logger.info("")
        logger.info("=" * 70)
        logger.info("UNIFIED PAPER TRADING - FINAL REPORT")
        logger.info("=" * 70)

        total_pnl = 0
        total_trades = 0
        total_wins = 0

        for exchange in [self.hibachi, self.extended, self.paradex]:
            stats = exchange.get_stats()
            total_pnl += stats['total_pnl'] + stats['unrealized_pnl']
            total_trades += stats['trades']
            total_wins += stats['wins']

            logger.info("")
            logger.info(f"[{exchange.name}]")
            logger.info(f"  Initial: ${stats['initial']:.2f}")
            logger.info(f"  Final Balance: ${stats['balance']:.2f}")
            logger.info(f"  Unrealized P&L: ${stats['unrealized_pnl']:+.2f}")
            logger.info(f"  Total Equity: ${stats['total_equity']:.2f}")
            logger.info(f"  Realized P&L: ${stats['total_pnl']:+.2f}")
            logger.info(f"  Return: {(stats['total_equity'] - stats['initial']) / stats['initial'] * 100:+.2f}%")
            logger.info(f"  Trades: {stats['trades']} (W: {stats['wins']}, L: {stats['losses']})")
            logger.info(f"  Win Rate: {stats['win_rate']:.1f}%")
            logger.info(f"  Volume: ${stats['volume']:,.2f}")

            # Show trade history
            if exchange.closed_trades:
                logger.info(f"  Trade History:")
                for trade in exchange.closed_trades:
                    emoji = "✅" if trade['pnl'] > 0 else "❌"
                    logger.info(f"    {emoji} {trade['side']} {trade['symbol']}: "
                               f"${trade['pnl']:+.2f} ({trade['pnl_pct']:+.1f}%) - {trade['reason']}")

        logger.info("")
        logger.info("=" * 70)
        logger.info("COMBINED RESULTS:")
        logger.info(f"  Total P&L (realized + unrealized): ${total_pnl:+.2f}")
        logger.info(f"  Total Return: {total_pnl / 300 * 100:+.2f}% on $300")
        logger.info(f"  Total Trades: {total_trades}")
        logger.info(f"  Overall Win Rate: {total_wins / max(1, total_trades) * 100:.1f}%")
        logger.info("=" * 70)

    def health_check(self, all_data: Dict) -> bool:
        """Validate data from all exchanges - FAIL FAST if something's broken"""
        issues = []

        # Check Hibachi
        hibachi_symbols = len(all_data.get('hibachi', {}))
        if hibachi_symbols == 0:
            issues.append("❌ HIBACHI: No data!")
        elif hibachi_symbols < 3:
            issues.append(f"⚠️ HIBACHI: Only {hibachi_symbols}/3 symbols")
        else:
            logger.info(f"✅ Hibachi: {hibachi_symbols} symbols")

        # Check Extended
        extended_symbols = len(all_data.get('extended', {}))
        if extended_symbols == 0:
            issues.append("❌ EXTENDED: No data!")
        elif extended_symbols < 3:
            issues.append(f"⚠️ EXTENDED: Only {extended_symbols}/3 symbols")
        else:
            logger.info(f"✅ Extended: {extended_symbols} symbols")

        # Check Paradex
        paradex_symbols = len(all_data.get('paradex', {}))
        if paradex_symbols == 0:
            issues.append("❌ PARADEX: No data!")
        else:
            logger.info(f"✅ Paradex: {paradex_symbols} symbols")

        # Report issues
        if issues:
            logger.warning("=" * 50)
            logger.warning("HEALTH CHECK ISSUES:")
            for issue in issues:
                logger.warning(f"  {issue}")
            logger.warning("=" * 50)

        # Only fail if ALL exchanges have no data
        total_symbols = hibachi_symbols + extended_symbols + paradex_symbols
        if total_symbols == 0:
            logger.error("🚨 CRITICAL: No data from ANY exchange! Aborting.")
            return False

        return True

    async def run(self):
        """Main trading loop"""
        await self.initialize()

        end_time = self.start_time + timedelta(hours=self.duration_hours)
        cycle = 0

        try:
            while datetime.now() < end_time:
                cycle += 1

                # Fetch data
                all_data = await self.fetch_all_data()

                # Health check - validate all exchanges have data
                if cycle == 1:
                    logger.info("\n🔍 INITIAL HEALTH CHECK:")
                    if not self.health_check(all_data):
                        logger.error("Health check failed on first cycle - fix data issues before continuing!")
                        return
                elif cycle % 3 == 0:  # Check every 3rd cycle
                    logger.info("\n🔍 Periodic health check:")
                    self.health_check(all_data)

                # Print status
                self.print_status(cycle, all_data)

                # Execute trading cycle
                await self.execute_cycle(all_data)

                # Wait for next cycle
                remaining = (end_time - datetime.now()).total_seconds() / 60
                logger.info(f"\n⏳ {remaining:.0f} min remaining | Next cycle in {self.cycle_minutes} min...")

                await asyncio.sleep(self.cycle_minutes * 60)

        except KeyboardInterrupt:
            logger.info("\n👋 Stopping by user request...")
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.print_final_report()


async def main():
    """Run the unified paper trading test"""
    import argparse

    parser = argparse.ArgumentParser(description='Unified Paper Trading Test')
    parser.add_argument('--hours', type=float, default=2.0,
                        help='Duration in hours (default: 2)')
    parser.add_argument('--cycle', type=int, default=10,
                        help='Cycle interval in minutes (default: 10)')

    args = parser.parse_args()

    trader = UnifiedPaperTrader(
        duration_hours=args.hours,
        cycle_minutes=args.cycle
    )
    await trader.run()


if __name__ == "__main__":
    asyncio.run(main())
