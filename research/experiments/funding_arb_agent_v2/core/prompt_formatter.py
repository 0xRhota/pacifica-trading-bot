"""
Prompt Formatter for LLM Funding Arbitrage
==========================================
Formats aggregated data into a structured prompt for the LLM.
Includes all data recommended by Qwen's review.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from .data_aggregator import AggregatedData, SpreadData

logger = logging.getLogger(__name__)

# Trend symbols for readability
TREND_SYMBOLS = {
    "rising": "",
    "falling": "",
    "stable": "",
    "widening": "",
    "narrowing": "",
    "mixed": ""
}


class PromptFormatter:
    """Formats data into LLM prompts for funding arbitrage decisions"""

    def __init__(self, config):
        self.config = config

    def format_decision_prompt(self, data: AggregatedData) -> str:
        """
        Format a complete decision prompt for the LLM.

        Includes:
        - System context and rules
        - Funding rates with trends
        - Spread analysis
        - Volatility metrics
        - Current positions
        - Account status
        - Funding clock
        """
        sections = [
            self._format_system_context(),
            self._format_funding_rates(data),
            self._format_spread_analysis(data),
            self._format_volatility(data),
            self._format_positions(data),
            self._format_account_status(data),
            self._format_funding_clock(data),
            self._format_decision_request()
        ]

        return "\n".join(sections)

    def _format_system_context(self) -> str:
        """System context and absolute rules"""
        return f"""=== DELTA-NEUTRAL FUNDING RATE ARBITRAGE ===

You are managing a delta-neutral funding rate arbitrage strategy across Hibachi and Extended exchanges.

ABSOLUTE RULES (code-enforced, cannot be overridden):
1. Positions MUST be EQUAL USD value on both exchanges
2. Positions MUST be OPPOSITE directions (one LONG, one SHORT)
3. You can ONLY trade the SAME asset on both exchanges
4. Maximum position size: ${self.config.max_position_usd:.2f} per leg

YOUR DECISIONS:
- Which asset to trade (BTC, ETH, or SOL)
- When to OPEN a new position
- When to CLOSE an existing position
- When to ROTATE (close and reopen with potentially different asset)
- When to HOLD (do nothing)

STRATEGY GOAL:
Capture funding rate differential by being SHORT on the exchange with higher rate
(to receive funding) and LONG on the exchange with lower rate (to pay less).
"""

    def _format_funding_rates(self, data: AggregatedData) -> str:
        """Format funding rates with trends"""
        lines = [
            "\n=== FUNDING RATES (8-hour settlement) ===",
            "",
            f"{'Asset':<6} {'Hibachi Rate':<14} {'Trend':<8} {'Extended Rate':<14} {'Trend':<8}",
            "-" * 60
        ]

        for symbol in self.config.symbols:
            if symbol not in data.funding:
                lines.append(f"{symbol:<6} {'N/A':<14} {'':<8} {'N/A':<14} {'':<8}")
                continue

            h = data.funding[symbol].get("Hibachi")
            e = data.funding[symbol].get("Extended")

            h_rate = f"{h.rate:+.6f}" if h else "N/A"
            h_trend = TREND_SYMBOLS.get(h.trend, "") if h else ""
            e_rate = f"{e.rate:+.6f}" if e else "N/A"
            e_trend = TREND_SYMBOLS.get(e.trend, "") if e else ""

            lines.append(f"{symbol:<6} {h_rate:<14} {h_trend:<8} {e_rate:<14} {e_trend:<8}")

        # Add annualized rates
        lines.append("")
        lines.append("Annualized Rates:")
        for symbol in self.config.symbols:
            if symbol not in data.funding:
                continue
            h = data.funding[symbol].get("Hibachi")
            e = data.funding[symbol].get("Extended")
            if h and e:
                lines.append(f"  {symbol}: Hibachi {h.annualized:+.2f}%, Extended {e.annualized:+.2f}%")

        return "\n".join(lines)

    def _format_spread_analysis(self, data: AggregatedData) -> str:
        """Format spread analysis with recommendations"""
        lines = [
            "\n=== SPREAD ANALYSIS ===",
            "",
            f"{'Asset':<6} {'Spread':<12} {'Annualized':<12} {'Trend':<10} {'Strategy':<30}",
            "-" * 75
        ]

        # Sort by annualized spread (best opportunity first)
        sorted_spreads = sorted(
            data.spreads.items(),
            key=lambda x: x[1].annualized_spread,
            reverse=True
        )

        for symbol, spread in sorted_spreads:
            trend_symbol = TREND_SYMBOLS.get(spread.trend, "")
            strategy = f"SHORT {spread.short_exchange}, LONG {spread.long_exchange}"

            # Mark if viable
            viable = "" if spread.annualized_spread >= self.config.min_spread_annualized else ""

            lines.append(
                f"{symbol:<6} {spread.spread:.6f}   {spread.annualized_spread:>6.2f}%      "
                f"{trend_symbol:<10} {strategy:<30} {viable}"
            )

        # Add expected returns
        lines.append("")
        lines.append("Expected Daily Returns (per $100 position):")
        for symbol, spread in sorted_spreads:
            lines.append(f"  {symbol}: ${spread.expected_daily_return:.4f}/day")

        # Highlight best opportunity
        if sorted_spreads:
            best = sorted_spreads[0]
            lines.append("")
            lines.append(f"BEST OPPORTUNITY: {best[0]} with {best[1].annualized_spread:.2f}% annualized spread")

        return "\n".join(lines)

    def _format_volatility(self, data: AggregatedData) -> str:
        """Format volatility metrics"""
        lines = [
            "\n=== VOLATILITY (Risk Assessment) ===",
            "",
            f"{'Asset':<6} {'1H Vol':<10} {'1H Change':<12} {'Status':<10}",
            "-" * 45
        ]

        for symbol in self.config.symbols:
            vol = data.volatility.get(symbol)
            if not vol:
                lines.append(f"{symbol:<6} {'N/A':<10} {'N/A':<12} {'UNKNOWN':<10}")
                continue

            status = "SAFE" if vol.is_safe else "HIGH RISK"
            lines.append(
                f"{symbol:<6} {vol.volatility_1h:>6.2f}%   {vol.price_change_1h:>+8.2f}%    {status:<10}"
            )

        # Warning if any volatility is high
        high_vol_assets = [s for s, v in data.volatility.items() if v and not v.is_safe]
        if high_vol_assets:
            lines.append("")
            lines.append(f"WARNING: High volatility on {', '.join(high_vol_assets)} - consider avoiding")

        return "\n".join(lines)

    def _format_positions(self, data: AggregatedData) -> str:
        """Format current positions"""
        lines = ["\n=== CURRENT POSITIONS ===", ""]

        if not data.positions:
            lines.append("No open positions.")
            return "\n".join(lines)

        # Group by symbol
        positions_by_symbol = {}
        for pos in data.positions:
            if pos.symbol not in positions_by_symbol:
                positions_by_symbol[pos.symbol] = []
            positions_by_symbol[pos.symbol].append(pos)

        for symbol, positions in positions_by_symbol.items():
            lines.append(f"{symbol}:")
            for pos in positions:
                pnl_str = f"${pos.unrealized_pnl:+.2f}" if pos.unrealized_pnl else "$0.00"
                lines.append(
                    f"  {pos.exchange}: {pos.side} ${pos.notional:.2f} | Entry: ${pos.entry_price:.2f} | PnL: {pnl_str}"
                )

        # Check delta neutrality
        for symbol, positions in positions_by_symbol.items():
            if len(positions) == 2:
                sides = {p.side for p in positions}
                notionals = [p.notional for p in positions]

                if sides == {"LONG", "SHORT"}:
                    delta = abs(notionals[0] - notionals[1])
                    if delta < notionals[0] * 0.1:  # Within 10%
                        lines.append(f"\n{symbol}: Delta-neutral (imbalance: ${delta:.2f})")
                    else:
                        lines.append(f"\n{symbol}: IMBALANCED (delta: ${delta:.2f})")
                else:
                    lines.append(f"\n{symbol}: NOT DELTA-NEUTRAL (both {sides})")
            elif len(positions) == 1:
                lines.append(f"\n{symbol}: EXPOSED (only {positions[0].exchange} {positions[0].side})")

        return "\n".join(lines)

    def _format_account_status(self, data: AggregatedData) -> str:
        """Format account balances and capacity"""
        return f"""
=== ACCOUNT STATUS ===

Balances:
  Hibachi:  ${data.hibachi_balance:.2f}
  Extended: ${data.extended_balance:.2f}

Position Capacity:
  Max position per leg: ${data.max_position_size:.2f}
  (Limited by smaller account balance)
"""

    def _format_funding_clock(self, data: AggregatedData) -> str:
        """Format time until next funding payment"""
        lines = ["\n=== FUNDING CLOCK ===", ""]

        if data.next_funding_time and data.hours_until_funding is not None:
            lines.append(f"Next funding payment in: {data.hours_until_funding:.1f} hours")
            lines.append(f"Time: {data.next_funding_time.strftime('%Y-%m-%d %H:%M UTC')}")

            # Calculate expected payment for best spread
            if data.spreads:
                best_symbol = max(data.spreads.keys(), key=lambda s: data.spreads[s].annualized_spread)
                best_spread = data.spreads[best_symbol]
                # Payment per $100 per 8h period
                payment_per_100 = best_spread.spread * 100
                lines.append(f"\nExpected funding payment ({best_symbol} @ $100/leg): ${payment_per_100:.4f}")
        else:
            lines.append("Funding clock not available")

        return "\n".join(lines)

    def _format_decision_request(self) -> str:
        """Format the decision request"""
        return """
=== DECISION REQUIRED ===

Based on the data above, provide your decision in the following JSON format:

```json
{{
  "action": "OPEN" | "CLOSE" | "ROTATE" | "HOLD",
  "asset": "BTC" | "ETH" | "SOL",
  "direction": {{
    "hibachi": "SHORT" | "LONG",
    "extended": "SHORT" | "LONG"
  }},
  "reasoning": "Your detailed reasoning here",
  "confidence": 0.0 to 1.0
}}
```

DECISION GUIDELINES:
- OPEN: When no position exists and spread is attractive (>{min_spread}% annualized)
- CLOSE: When spread has degraded below threshold or market conditions unfavorable
- ROTATE: When a better opportunity exists in a different asset
- HOLD: When current position is optimal or no good opportunities exist

IMPORTANT:
- Only recommend OPEN/ROTATE if confidence >= {min_conf}
- Always SHORT the exchange with HIGHER funding rate
- Always LONG the exchange with LOWER funding rate
- Consider volatility - avoid high-volatility assets
- Consider spread trend - widening is good, narrowing is warning

Provide your decision now:
""".format(
            min_spread=self.config.min_spread_annualized,
            min_conf=self.config.min_confidence
        )
