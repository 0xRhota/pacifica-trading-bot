# Hopium Agents - Progress Tracker

**Last Updated:** 2026-01-09

---

## Currently Running

### Grid Market Making (Live)

Two Grid MM bots running the same strategy on different exchanges:

#### Paradex Grid MM (BTC-USD-PERP)
**Status**: RUNNING
**Script**: `scripts/grid_mm_live.py`
**Log**: `logs/grid_mm_live.log`

**Configuration**:
- Symbol: BTC-USD-PERP
- Spread: 1.5 bps
- Order size: $100/order
- Levels: 2 per side ($200 per side)
- Max inventory: 300% (leveraged)
- ROC threshold: 3 bps (pause on trend)

**Start**:
```bash
nohup python3 scripts/grid_mm_live.py > logs/grid_mm_live.log 2>&1 &
```

#### Hibachi Grid MM (ETH/USDT-P)
**Status**: RUNNING
**Script**: `scripts/grid_mm_hibachi.py`
**Log**: `logs/hibachi_grid_mm.log`

**Configuration**:
- Symbol: ETH/USDT-P
- Spread: 2 bps
- Order size: $100/order
- Levels: 2 per side ($200 per side)
- Max inventory: 300% (leveraged)
- ROC threshold: 5 bps (pause on trend)

**Start**:
```bash
nohup python3 -u scripts/grid_mm_hibachi.py > logs/hibachi_grid_mm.log 2>&1 &
```

**Strategy**:
Both bots place limit orders on both sides of mid price. When orders fill, they earn the spread. ROC (Rate of Change) trend detection pauses orders during strong moves to avoid adverse fills.

**Stop all**:
```bash
pkill -f grid_mm_live && pkill -f grid_mm_hibachi
```

---

## Exchange Accounts

| Exchange | Balance | Bot Running |
|----------|---------|-------------|
| Hibachi | ~$68 | Grid MM (ETH) |
| Paradex | ~$73 | Grid MM (BTC) |
| Extended | ~$100 | — |

---

## Recent Changes (2026-01-08/09)

### Hibachi Grid MM Implementation
- Added `create_limit_order()` to Hibachi SDK
- Implemented Hibachi price formula: `price * 2^32 * 10^(settlementDecimals - underlyingDecimals)`
- Created `scripts/grid_mm_hibachi.py` mirroring Paradex strategy

### Paradex Grid MM Updates
- Increased order size from $50 to $100
- Increased max inventory from 200% to 300%
- Enhanced trend detection with ROC thresholds

### Self-Learning Updates
- Added user notes/working memory system for LLM bots
- File: `logs/user_notes.json`

---

## Key Files

| Purpose | File |
|---------|------|
| Paradex Grid MM | `scripts/grid_mm_live.py` |
| Hibachi Grid MM | `scripts/grid_mm_hibachi.py` |
| Hibachi SDK | `dexes/hibachi/hibachi_sdk.py` |
| Paper trade test | `scripts/unified_paper_trade.py` |
| Data validation | `scripts/monitor_paper_trade_v2.py` |
| Funding rate monitor | `scripts/funding_rate_monitor.py` |
| Trade analysis | `scripts/analyze_all_trades.py` |

---

## Philosophy

**Grid Market Making**:
- Earn spread by providing liquidity
- Pause during strong trends (ROC detection)
- Use leverage for capital efficiency

**LLM Swing Trading** (when enabled):
- 6 trades/day max
- 8% TP, 4% SL (2:1 R/R minimum)
- 48h max hold
- Cut losers after 4h if underwater
