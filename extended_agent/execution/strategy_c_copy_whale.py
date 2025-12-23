"""
Strategy C - Copy Whale Portfolio (for Extended)
Whale: 0x023a3d058020fb76cca98f01b3c48c8938a22355

PHILOSOPHY:
Copy a proven whale's BTC/ETH/SOL portfolio allocation percentages.
Use PROPORTIONAL sizing - match whale's % allocation, not absolute dollars.

MECHANICS:
- Poll whale's Hyperliquid positions every 5 minutes
- Calculate whale's % allocation to BTC, ETH, SOL
- Mirror those % allocations with our Extended account balance
- Execute rebalancing trades on Extended DEX

EXAMPLE:
Whale account: $28.8M
  - BTC: $36M (64% of portfolio - overleveraged long)
  - ETH: $8.7M (15%)
  - SOL: $11.7M (20%)

Our account: $77
  - BTC target: $77 × 64% = $49.28
  - ETH target: $77 × 15% = $11.55
  - SOL target: $77 × 20% = $15.40

ADVANTAGES:
- Leverage whale's $966K unrealized profit expertise
- 28 trades/min activity = constantly optimized positions
- No LLM costs - just follow proven trader
- Auto-rebalances as whale adjusts positions

EXIT RULES:
- None - purely follow whale's positions
- If whale closes, we close
- If whale adds, we add (proportionally)
"""

import logging
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class StrategyC_CopyWhale:
    """
    Copy whale's BTC/ETH/SOL portfolio allocation percentages

    Target whale: 0x023a (Multi-Asset Scalper)
    - $28.8M account
    - 28 trades/min
    - +$966K unrealized on BTC/ETH/SOL
    """

    STRATEGY_NAME = "STRATEGY_C_COPY_WHALE"

    # Whale configuration
    WHALE_ADDRESS = "0x023a3d058020fb76cca98f01b3c48c8938a22355"
    WHALE_NAME = "Multi-Asset Scalper (0x023a)"
    HYPERLIQUID_API = "https://api.hyperliquid.xyz/info"

    # Assets to copy (Extended has BTC, ETH, SOL)
    COPY_ASSETS = ["BTC", "ETH", "SOL"]

    # Rebalancing threshold (only rebalance if allocation differs by >5%)
    REBALANCE_THRESHOLD_PCT = 5.0

    def __init__(self):
        """Initialize Strategy C"""
        self.last_whale_positions = {}
        self.last_fetch_time = None

        logger.info("=" * 60)
        logger.info(f"STRATEGY C: COPY WHALE")
        logger.info(f"  Whale: {self.WHALE_NAME}")
        logger.info(f"  Address: {self.WHALE_ADDRESS}")
        logger.info(f"  Assets: {', '.join(self.COPY_ASSETS)}")
        logger.info(f"  Rebalance Threshold: ±{self.REBALANCE_THRESHOLD_PCT}%")
        logger.info("=" * 60)

    async def fetch_whale_positions(self) -> Dict[str, Dict]:
        """
        Fetch whale's current positions from Hyperliquid API

        Returns:
            Dict mapping coin -> position info
        """
        try:
            payload = {
                "type": "clearinghouseState",
                "user": self.WHALE_ADDRESS
            }

            response = requests.post(
                self.HYPERLIQUID_API,
                json=payload,
                timeout=10
            )

            if response.status_code != 200:
                logger.error(f"Hyperliquid API error: {response.status_code}")
                return {}

            data = response.json()
            margin = data.get('marginSummary', {})
            positions = data.get('assetPositions', [])

            # Extract whale's account value
            whale_account_value = float(margin.get('accountValue', 0))

            # Extract BTC/ETH/SOL positions
            whale_positions = {}
            for p in positions:
                pos = p.get('position', {})
                coin = pos.get('coin', '')

                if coin in self.COPY_ASSETS:
                    size = float(pos.get('szi', 0))
                    if size != 0:
                        entry_price = float(pos.get('entryPx', 0))
                        notional = abs(size * entry_price)
                        side = 'long' if size > 0 else 'short'

                        whale_positions[coin] = {
                            'size': size,
                            'side': side,
                            'notional': notional,
                            'entry_price': entry_price
                        }

            # Calculate allocations
            total_btc_eth_sol_notional = sum(p['notional'] for p in whale_positions.values())

            for coin, pos in whale_positions.items():
                pos['allocation_pct'] = (pos['notional'] / whale_account_value * 100) if whale_account_value > 0 else 0

            logger.info("")
            logger.info("=" * 60)
            logger.info(f"[STRATEGY-C] WHALE POSITIONS")
            logger.info(f"  Account: ${whale_account_value:,.0f}")
            logger.info(f"  BTC/ETH/SOL Total: ${total_btc_eth_sol_notional:,.0f}")

            for coin in self.COPY_ASSETS:
                if coin in whale_positions:
                    p = whale_positions[coin]
                    logger.info(f"  {coin}: {p['side'].upper()} ${p['notional']:,.0f} ({p['allocation_pct']:.1f}% of account)")
                else:
                    logger.info(f"  {coin}: FLAT (0%)")
            logger.info("=" * 60)
            logger.info("")

            self.last_whale_positions = whale_positions
            self.last_fetch_time = datetime.now()

            return whale_positions

        except Exception as e:
            logger.error(f"Error fetching whale positions: {e}")
            return {}

    def calculate_target_positions(
        self,
        whale_positions: Dict[str, Dict],
        our_account_balance: float,
        current_positions: List[Dict]
    ) -> List[Dict]:
        """
        Calculate what our positions should be to match whale's allocation

        Args:
            whale_positions: Whale's current positions
            our_account_balance: Our Extended account balance
            current_positions: Our current open positions

        Returns:
            List of rebalancing actions needed
        """
        actions = []

        # Build map of our current positions
        our_positions_map = {}
        for pos in current_positions:
            symbol = pos.get('symbol', '').replace('-USD', '')  # BTC-USD -> BTC
            if symbol in self.COPY_ASSETS:
                our_positions_map[symbol] = pos

        # For each asset, calculate target vs current
        for coin in self.COPY_ASSETS:
            # Whale's allocation
            if coin in whale_positions:
                whale_pct = whale_positions[coin]['allocation_pct']
                whale_side = whale_positions[coin]['side']
                target_notional = our_account_balance * (whale_pct / 100)
            else:
                # Whale has no position
                whale_pct = 0
                whale_side = None
                target_notional = 0

            # Our current position
            symbol = f"{coin}-USD"
            if coin in our_positions_map:
                our_pos = our_positions_map[coin]
                our_notional = abs(float(our_pos.get('value', 0)))
                our_side = our_pos.get('side', '').lower()
                our_pct = (our_notional / our_account_balance * 100) if our_account_balance > 0 else 0
            else:
                our_notional = 0
                our_side = None
                our_pct = 0

            # Calculate allocation difference
            allocation_diff = abs(whale_pct - our_pct)

            # Determine if rebalancing needed
            needs_rebalance = allocation_diff >= self.REBALANCE_THRESHOLD_PCT

            # Generate action
            if needs_rebalance:
                if whale_pct == 0:
                    # Whale flat, we should close
                    actions.append({
                        'action': 'CLOSE',
                        'symbol': symbol,
                        'coin': coin,
                        'reason': f"Whale closed {coin} position (0% allocation)",
                        'current_pct': our_pct,
                        'target_pct': 0
                    })
                elif our_pct == 0:
                    # We're flat, whale has position - open new
                    actions.append({
                        'action': 'LONG' if whale_side == 'long' else 'SHORT',
                        'symbol': symbol,
                        'coin': coin,
                        'target_usd': target_notional,
                        'reason': f"Whale allocated {whale_pct:.1f}% to {coin} {whale_side.upper()}",
                        'current_pct': 0,
                        'target_pct': whale_pct
                    })
                elif our_side == whale_side:
                    # Same direction, adjust size
                    if target_notional > our_notional:
                        actions.append({
                            'action': 'ADD',
                            'symbol': symbol,
                            'coin': coin,
                            'target_usd': target_notional,
                            'current_usd': our_notional,
                            'reason': f"Whale increased {coin} to {whale_pct:.1f}%",
                            'current_pct': our_pct,
                            'target_pct': whale_pct
                        })
                    else:
                        actions.append({
                            'action': 'REDUCE',
                            'symbol': symbol,
                            'coin': coin,
                            'target_usd': target_notional,
                            'current_usd': our_notional,
                            'reason': f"Whale reduced {coin} to {whale_pct:.1f}%",
                            'current_pct': our_pct,
                            'target_pct': whale_pct
                        })
                else:
                    # Different direction - close and reopen
                    actions.append({
                        'action': 'CLOSE_AND_REVERSE',
                        'symbol': symbol,
                        'coin': coin,
                        'new_side': 'LONG' if whale_side == 'long' else 'SHORT',
                        'target_usd': target_notional,
                        'reason': f"Whale flipped {coin} to {whale_side.upper()} ({whale_pct:.1f}%)",
                        'current_pct': our_pct,
                        'target_pct': whale_pct
                    })

        return actions

    def log_rebalancing_plan(self, actions: List[Dict]) -> None:
        """Log the rebalancing actions that will be taken"""
        if not actions:
            logger.info("[STRATEGY-C] No rebalancing needed - positions match whale")
            return

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"[STRATEGY-C] REBALANCING PLAN ({len(actions)} actions)")
        logger.info("=" * 60)

        for i, action in enumerate(actions, 1):
            act = action['action']
            coin = action['coin']
            reason = action['reason']
            curr_pct = action.get('current_pct', 0)
            tgt_pct = action.get('target_pct', 0)

            logger.info(f"{i}. {act} {coin}")
            logger.info(f"   Allocation: {curr_pct:.1f}% → {tgt_pct:.1f}%")
            logger.info(f"   Reason: {reason}")

        logger.info("=" * 60)
        logger.info("")

    def get_status_summary(self) -> Dict:
        """Get current strategy status for logging"""
        return {
            "strategy": self.STRATEGY_NAME,
            "whale": self.WHALE_NAME,
            "assets": self.COPY_ASSETS,
            "last_fetch": self.last_fetch_time.strftime("%H:%M:%S") if self.last_fetch_time else "Never",
            "rebalance_threshold": f"±{self.REBALANCE_THRESHOLD_PCT}%"
        }

    async def get_copy_decisions(
        self,
        our_positions: List[Dict],
        account_balance: float
    ) -> List[Dict]:
        """
        Main entry point: Get copy decisions based on whale's current positions.

        Args:
            our_positions: Our current open positions
            account_balance: Our account balance in USD

        Returns:
            List of trade decisions (in format ready for executor)
        """
        # Fetch whale's latest positions
        whale_positions = await self.fetch_whale_positions()

        if not whale_positions:
            logger.warning("[STRATEGY-C] Could not fetch whale positions - skipping cycle")
            return []

        # Calculate needed rebalancing actions
        actions = self.calculate_target_positions(
            whale_positions=whale_positions,
            our_account_balance=account_balance,
            current_positions=our_positions
        )

        # Log the plan
        self.log_rebalancing_plan(actions)

        if not actions:
            return []

        # Convert actions to executor-ready decisions
        decisions = []
        for action in actions:
            act = action['action']
            symbol = action['symbol']
            coin = action['coin']
            reason = action['reason']
            target_pct = action.get('target_pct', 0)

            if act in ['LONG', 'SHORT']:
                # New position - use target USD amount
                target_usd = action.get('target_usd', 0)
                decisions.append({
                    'action': act,
                    'symbol': symbol,
                    'reasoning': f"[COPY WHALE] {reason}",
                    'confidence': 0.9,  # High confidence in whale
                    'target_usd': target_usd
                })

            elif act == 'CLOSE':
                decisions.append({
                    'action': 'CLOSE',
                    'symbol': symbol,
                    'reasoning': f"[COPY WHALE] {reason}",
                    'confidence': 0.9
                })

            elif act == 'ADD':
                # Add to position - calculate delta
                current_usd = action.get('current_usd', 0)
                target_usd = action.get('target_usd', 0)
                add_usd = target_usd - current_usd

                # Convert to LONG/SHORT (same direction as existing)
                # We need to get the current side from our positions
                current_side = None
                for pos in our_positions:
                    if pos.get('symbol', '').replace('-USD', '') == coin:
                        current_side = pos.get('side', '').upper()
                        break

                if current_side:
                    decisions.append({
                        'action': current_side,  # LONG or SHORT
                        'symbol': symbol,
                        'reasoning': f"[COPY WHALE] Scale in: {reason}",
                        'confidence': 0.85,
                        'target_usd': add_usd
                    })

            elif act == 'REDUCE':
                # Reduce position - partial close
                current_usd = action.get('current_usd', 0)
                target_usd = action.get('target_usd', 0)
                reduce_pct = ((current_usd - target_usd) / current_usd) * 100

                # For now, if whale reduces significantly, close entirely
                # (Complex partial closes not implemented yet)
                if reduce_pct > 50:
                    decisions.append({
                        'action': 'CLOSE',
                        'symbol': symbol,
                        'reasoning': f"[COPY WHALE] Scale out: {reason}",
                        'confidence': 0.8
                    })
                else:
                    logger.info(f"[STRATEGY-C] {coin} reduce {reduce_pct:.0f}% too small, skipping")

            elif act == 'CLOSE_AND_REVERSE':
                # Close current position
                decisions.append({
                    'action': 'CLOSE',
                    'symbol': symbol,
                    'reasoning': f"[COPY WHALE] Close for reversal: {reason}",
                    'confidence': 0.9
                })
                # Open new position in opposite direction
                new_side = action.get('new_side', 'LONG')
                target_usd = action.get('target_usd', 0)
                decisions.append({
                    'action': new_side,
                    'symbol': symbol,
                    'reasoning': f"[COPY WHALE] Reverse: {reason}",
                    'confidence': 0.9,
                    'target_usd': target_usd
                })

        return decisions
