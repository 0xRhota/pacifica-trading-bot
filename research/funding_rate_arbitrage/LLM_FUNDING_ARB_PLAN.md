# LLM-Driven Delta-Neutral Funding Rate Arbitrage Bot

## Executive Summary

Replace the rule-based `funding_arb_agent` with an LLM-driven approach that uses a single LLM to make coordinated decisions across both Hibachi and Extended exchanges, while maintaining strict delta-neutral constraints.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM Funding Arb Bot                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Hibachi    │    │   Extended   │    │   LLM        │  │
│  │   Adapter    │    │   Adapter    │    │   Client     │  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
│         │                   │                   │           │
│         └─────────┬─────────┘                   │           │
│                   │                             │           │
│         ┌─────────▼─────────┐                   │           │
│         │  Data Aggregator  │                   │           │
│         │  - Funding rates  │                   │           │
│         │  - Positions      │                   │           │
│         │  - Balances       │                   │           │
│         └─────────┬─────────┘                   │           │
│                   │                             │           │
│         ┌─────────▼─────────────────────────────▼───────┐  │
│         │              Prompt Formatter                  │  │
│         │  - Format funding data for LLM                 │  │
│         │  - Include constraints (equal sizing, etc)     │  │
│         └─────────┬─────────────────────────────────────┘  │
│                   │                                         │
│         ┌─────────▼─────────┐                              │
│         │   LLM Decision    │                              │
│         │   - Asset select  │                              │
│         │   - Direction     │                              │
│         │   - Entry/exit    │                              │
│         └─────────┬─────────┘                              │
│                   │                                         │
│         ┌─────────▼─────────┐                              │
│         │  Delta-Neutral    │ ◄── STRICT ENFORCEMENT       │
│         │  Executor         │     (Not LLM controlled)     │
│         │  - Equal sizes    │                              │
│         │  - Opposite dirs  │                              │
│         │  - Atomic exec    │                              │
│         └───────────────────┘                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

### 1. What the LLM Controls

| Decision | LLM Control | Rationale |
|----------|-------------|-----------|
| Which asset to trade (BTC/ETH/SOL) | ✅ YES | LLM can reason about which spread is most attractive |
| When to enter | ✅ YES | LLM can consider market context |
| When to exit/rotate | ✅ YES | LLM can judge if spread is degrading |
| Position direction | ✅ YES | Short high-rate, long low-rate (LLM verifies) |
| Whether to trade at all | ✅ YES | LLM can say "NO_TRADE" if conditions poor |

### 2. What the Code Controls (NOT LLM)

| Constraint | Code Enforced | Rationale |
|------------|---------------|-----------|
| Equal position sizes | ✅ ALWAYS | Delta neutrality is mathematical, not discretionary |
| Opposite directions | ✅ ALWAYS | Can't have two longs or two shorts |
| Max position size | ✅ ALWAYS | Risk management |
| Execution atomicity | ✅ ALWAYS | Both legs must succeed or neither |

### 3. Position Sizing Logic

```python
# Code-enforced, NOT LLM decision
def calculate_position_size(hibachi_balance, extended_balance, config):
    # Use smaller balance as constraint
    available = min(hibachi_balance, extended_balance)

    # Max 80% of smaller account (leave margin buffer)
    max_size = available * 0.80

    # Apply configured limits
    position_size = min(max_size, config.max_position_size_usd)

    return position_size  # Same size used on BOTH exchanges
```

---

## Prompt Design

### System Context
```
You are a delta-neutral funding rate arbitrage specialist managing positions across two exchanges: Hibachi and Extended.

ABSOLUTE RULES (cannot be overridden):
1. Positions MUST be equal USD value on both exchanges
2. Positions MUST be opposite directions (one LONG, one SHORT)
3. You can only trade the SAME asset on both exchanges
4. Maximum position size per leg: ${max_size}

Your job is to:
1. Analyze funding rate differentials
2. Decide WHICH asset has the best opportunity
3. Decide WHEN to enter, exit, or rotate positions
4. The execution system will handle equal sizing automatically
```

### Data Provided to LLM
```
=== FUNDING RATES (8-hour settlement) ===

Asset    | Hibachi Rate | Extended Rate | Spread | Annualized
---------|--------------|---------------|--------|------------
BTC      | +0.0100%     | -0.0050%      | 0.015% | 16.4%
ETH      | +0.0080%     | +0.0020%      | 0.006% | 6.6%
SOL      | -0.0020%     | +0.0120%      | 0.014% | 15.3%

=== CURRENT POSITIONS ===
None (or details if positions exist)

=== ACCOUNT STATUS ===
Hibachi Balance: $89.21
Extended Balance: $45.77
Max Position Size: $36.62 per leg (80% of smaller balance)

=== RECENT HISTORY ===
Last trade: None
Session PnL: $0.00
```

### Expected LLM Output Format
```json
{
  "action": "OPEN" | "CLOSE" | "ROTATE" | "HOLD",
  "asset": "BTC" | "ETH" | "SOL",
  "direction": {
    "hibachi": "SHORT",
    "extended": "LONG"
  },
  "reasoning": "BTC has highest spread (16.4% annualized). Hibachi rate is higher (+0.01%) so we SHORT there to receive funding. Extended rate is negative (-0.005%) so we LONG there to receive funding on that side too. Net expected: ~16.4% annualized on the spread.",
  "confidence": 0.85
}
```

---

## File Structure

```
funding_arb_agent_v2/
├── __init__.py
├── bot_funding_arb_llm.py      # Main bot entry point
├── core/
│   ├── __init__.py
│   ├── config.py               # Configuration (reuse existing)
│   ├── data_aggregator.py      # Fetch data from both exchanges
│   ├── prompt_formatter.py     # Format prompt for LLM
│   ├── response_parser.py      # Parse LLM response
│   └── delta_neutral_executor.py  # Execute with strict constraints
├── exchanges/
│   ├── __init__.py
│   ├── hibachi_adapter.py      # Reuse from funding_arb_agent
│   └── extended_adapter.py     # Reuse from funding_arb_agent
└── prompts/
    └── funding_arb_system.txt  # System prompt template
```

---

## Execution Flow

```
1. FETCH DATA (every 5 minutes)
   ├── Get funding rates from Hibachi (BTC, ETH, SOL)
   ├── Get funding rates from Extended (BTC, ETH, SOL)
   ├── Get current positions on both exchanges
   └── Get account balances

2. FORMAT PROMPT
   ├── Calculate spreads and annualized returns
   ├── Include position constraints
   └── Add recent trade history

3. LLM DECISION
   ├── Send prompt to Qwen/DeepSeek
   ├── Parse structured response
   └── Validate response format

4. EXECUTE (if action != HOLD)
   ├── Calculate equal position size (code-enforced)
   ├── Validate directions are opposite (code-enforced)
   ├── Execute on Exchange A
   ├── If success: Execute on Exchange B
   ├── If Exchange B fails: Rollback Exchange A
   └── Log results

5. WAIT & REPEAT
```

---

## Risk Controls

### Code-Enforced (Cannot Be Bypassed)
1. **Equal sizing**: Both legs always same USD value
2. **Opposite directions**: Validated before execution
3. **Same asset**: Cannot open BTC on one and ETH on other
4. **Balance check**: Never exceed 80% of smaller account
5. **Atomic execution**: Rollback if second leg fails

### LLM-Guided (Advisory)
1. **Minimum spread threshold**: LLM should reject <5% annualized
2. **Market conditions**: LLM can say NO_TRADE if volatility high
3. **Position age**: LLM decides when to rotate

---

## Configuration

```python
@dataclass
class LLMFundingArbConfig:
    # Timing
    scan_interval: int = 300           # 5 minutes

    # Position sizing (code-enforced)
    max_position_pct: float = 0.80     # 80% of smaller balance
    max_position_usd: float = 100.0    # Hard cap per leg

    # LLM settings
    model: str = "qwen-max"            # Or "deepseek-chat"
    temperature: float = 0.1           # Low for consistency

    # Minimum spread (LLM advisory, but can be enforced)
    min_spread_annualized: float = 5.0  # 5% minimum

    # Execution
    dry_run: bool = True

    # Symbols to consider
    symbols: List[str] = ["BTC", "ETH", "SOL"]
```

---

## Advantages Over Rule-Based

| Aspect | Rule-Based | LLM-Driven |
|--------|------------|------------|
| Asset selection | Fixed rotation | Chooses best opportunity |
| Entry timing | Spread > threshold | Considers market context |
| Exit timing | Fixed rotation interval | Judges when spread degrading |
| Adaptability | Rigid rules | Can reason about edge cases |
| Explainability | None | Full reasoning in logs |

---

## Questions for Qwen Review

1. **Is the LLM scope appropriate?** Should it control more or less?

2. **Position sizing**: Should LLM have ANY input on size, or keep 100% code-enforced?

3. **Prompt structure**: Is the data format clear enough for consistent decisions?

4. **Failure handling**: If one leg fails, should we:
   - Always rollback?
   - Let LLM decide?
   - Have a rule-based fallback?

5. **Rotation strategy**: Should rotation be:
   - Time-based (every N hours)?
   - LLM-decided (when spread changes)?
   - Hybrid?

6. **Model choice**: Qwen-max vs DeepSeek for this use case?

---

## Implementation Estimate

- **Reusable components**: ~60% (exchange adapters, model client, config)
- **New components**: ~40% (prompt formatter, executor, main bot)
- **Testing**: Need dry-run validation before live

---

## Next Steps

1. Get Qwen review on this plan
2. Address feedback
3. Implement in `funding_arb_agent_v2/`
4. Test with dry-run mode
5. Deploy live with small position sizes
