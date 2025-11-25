# Winning Wallet Analysis - Pacifica

**Purpose**: Analyze successful trading patterns from profitable wallets on Pacifica to inform fee-aware strategies.

## Key Differences: Pacifica vs Lighter

### Pacifica Constraints
- **Fees**: 0.04% taker fee (both entry and exit = 0.08% round-trip)
- **Impact**: Need higher win rate or larger moves to overcome fees
- **Minimum profit**: ~0.1% after fees to break even

### Lighter (for comparison)
- **Fees**: 0% (zero fees)
- **Impact**: Any positive move = profit

## Research Questions

1. **Hold times**: How long do winning wallets hold positions?
   - Do they scalp (5-15 min) or swing (hours/days)?
   - Does longer hold time correlate with profitability?

2. **Position sizing**: What % of account do they risk?
   - Fixed size or dynamic?
   - Do they size up on winners?

3. **Win rate vs profit factor**:
   - High win rate (>60%) with small wins?
   - Lower win rate (40-50%) with large wins?

4. **Market conditions**:
   - Trade more in trending markets vs choppy?
   - Correlation with volatility (ATR)?

5. **Entry timing**:
   - Wait for pullbacks in trends?
   - Buy breakouts?
   - Mean reversion plays?

## Data Files

- `wallet_trades_raw.csv` - Raw trade data from winning wallets
- `wallet_analysis.md` - Analysis and findings
- `patterns.md` - Identified patterns and strategies

## Expected Insights

Since Pacifica has fees, winning strategies likely:
- Hold longer (to capture bigger moves)
- Trade less frequently (avoid death by 1000 cuts)
- Higher selectivity (only trade high-conviction setups)
- Possibly larger positions (offset fees with size)

This is different from Lighter where we can profitably scalp tiny moves due to zero fees.
