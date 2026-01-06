# Hopium Agents

LLM-powered trading agents for perpetual DEXs. Feed quant data (funding, OI, volume, RSI, MACD), let the model decide.

## Table of Contents
- [Quick Start](#quick-start)
- [Running a Bot](#running-a-bot)
- [Strategies](#strategies)
- [How the Bot Decides](#how-the-bot-decides)
- [Data Sources](#data-sources)
- [Logging System](#logging-system)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [Testing Results](#testing-results)

---

## Quick Start

```bash
git clone https://github.com/0xRhota/HopiumAgents.git
cd HopiumAgents
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your API keys:
```bash
OPEN_ROUTER=your_openrouter_key
CAMBRIAN_API_KEY=your_cambrian_key

# Exchange credentials (configure the ones you'll use)
HIBACHI_PUBLIC_KEY=...
HIBACHI_PRIVATE_KEY=...
```

---

## Running a Bot

### Example Commands

These are example configurations. See [docs/STRATEGIES.md](docs/STRATEGIES.md) for all available strategies and parameters.

```bash
# Example: Hibachi with self-improving strategy
python3 -m hibachi_agent.bot_hibachi --live --strategy F --interval 600

# Example: Lighter with default settings
python3 -m lighter_agent.bot_lighter --live --interval 300

# Example: Extended with pairs trading (requires Python 3.11+)
python3.11 -m extended_agent.bot_extended --live --strategy D --interval 300

# Example: Grid market making on Paradex
python3 scripts/grid_mm_live.py
```

### Common Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Simulate trades without executing (recommended for testing) |
| `--live` | Execute real trades |
| `--strategy X` | Select strategy (see [Strategy Reference](#strategies)) |
| `--interval N` | Seconds between decision cycles |

### Available Bots

| Bot | Exchange | Entry Point | Notes |
|-----|----------|-------------|-------|
| Hibachi | Hibachi DEX | `hibachi_agent.bot_hibachi` | Most strategy options |
| Lighter | Lighter DEX | `lighter_agent.bot_lighter` | Zero fees |
| Extended | Extended DEX | `extended_agent.bot_extended` | Requires Python 3.11+ |
| Paradex | Paradex | `scripts/grid_mm_live.py` | Grid market making |

---

## Strategies

Strategies are modular Python classes that control how the bot makes decisions. Each strategy lives in `{exchange}_agent/execution/strategy_{flag}_{name}.py`.

**Full documentation: [docs/STRATEGIES.md](docs/STRATEGIES.md)**

### Available Strategies

| Flag | Name | File | Description |
|------|------|------|-------------|
| `F` | Self-improving | `strategy_f_self_improving.py` | Tracks outcomes, auto-blocks losing patterns |
| `D` | Pairs trade | `strategy_d_pairs_trade.py` | Long one asset, short another (ETH/BTC) |
| `G` | Low-liq hunter | `strategy_g_low_liq_hunter.py` | Targets volatile pairs with trailing stops |
| `A` | Hard exits | `strategy_a_exit_rules.py` | Fixed TP/SL rules override LLM |
| `C` | Copy whale | `strategy_c_copy_whale.py` | Mirrors a specific wallet's positions |

### Selecting a Strategy

```bash
# Use --strategy flag
python3 -m hibachi_agent.bot_hibachi --live --strategy F

# Default (no flag) runs without strategy overlay
python3 -m hibachi_agent.bot_hibachi --live
```

### How Strategies Work

1. **The LLM decides** what to trade based on market data + prompt
2. **The strategy filters/modifies** that decision (block symbols, enforce exits, etc.)
3. **The executor** places orders on the exchange

Strategies can override LLM decisions. For example, Strategy A ignores LLM exit suggestions and uses hard TP/SL rules instead.

### Prompts

The LLM prompt determines how market data is interpreted. Prompts live in `llm_agent/prompts_archive/`.

| Prompt | Approach |
|--------|----------|
| `v9_qwen_enhanced.txt` | 5-signal scoring, 3:1 R:R (recommended) |
| `v1-v8` | Earlier iterations (see [STRATEGIES.md](docs/STRATEGIES.md#prompt-history)) |

### Grid Market Making

A separate market-making strategy for Paradex: `scripts/grid_mm_live.py`

| Parameter | Default | Description |
|-----------|---------|-------------|
| `spread_bps` | 1.5 | Spread in basis points |
| `pause_duration` | 15 | Seconds to pause after fills |
| `inventory_limit` | 25% | Max position as % of account |

See [research/strategies/GRID_MM_EVOLUTION.md](research/strategies/GRID_MM_EVOLUTION.md) for parameter tuning history.

---

## How the Bot Decides

```
1. Fetch Market Data
   └── Price, RSI, MACD, volume, funding rates, open interest

2. Build LLM Prompt
   └── Combines market data + strategy context + position state

3. Query LLM
   └── Qwen via OpenRouter (configurable)

4. Validate & Execute
   └── Parse response, validate against rules, place orders

5. Monitor Positions
   └── Check exit conditions each cycle (TP, SL, time limits)
```

The **strategy** determines:
- What data goes into the prompt
- How exit conditions are evaluated
- Position sizing rules

---

## Data Sources

The bots aggregate data from multiple sources. **Full reference: [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)**

### Market Data (Per Exchange)

| Data | Source | Update Frequency |
|------|--------|------------------|
| Price | Exchange API | Each cycle |
| Volume (24h) | Exchange API | Each cycle |
| Funding Rate | Exchange API | Each cycle |
| Open Interest | Exchange API | Each cycle |

### Technical Indicators (Calculated Locally)

| Indicator | Calculation | Purpose |
|-----------|-------------|---------|
| RSI | 14-period relative strength | Overbought/oversold |
| MACD | 12/26/9 EMA crossover | Trend momentum |
| EMA | Exponential moving average | Trend direction |
| SMA | Simple moving average | Baseline trend |

### External Data (Optional)

| Source | Endpoint | Purpose |
|--------|----------|---------|
| Cambrian Deep42 | `deep42.cambrian.network` | AI sentiment analysis |
| Fear & Greed Index | Alternative.me | Market sentiment |
| Funding Rates (Cross-Exchange) | Various | Arbitrage signals |

**Implementation**: `llm_agent/data/` directory contains all data fetchers.

---

## Logging System

All logs are written to the `logs/` directory (gitignored).

### Log Types

| Log File | Contents |
|----------|----------|
| `logs/{exchange}_bot.log` | Bot decisions, errors, cycle status |
| `logs/trades/{exchange}.json` | Complete trade history (JSON) |
| `logs/strategy_switches.log` | Strategy change history |
| `logs/shared_insights.json` | Cross-bot learning state |

### Trade Log Structure

Each exchange maintains its own trade log in `logs/trades/{exchange}.json`:

```json
{
  "timestamp": "2026-01-06T12:00:00",
  "dex": "hibachi",
  "symbol": "BTC/USDT-P",
  "side": "buy",
  "size": 0.001,
  "entry_price": 92000.00,
  "exit_price": 92500.00,
  "pnl": 0.50,
  "pnl_pct": 0.54,
  "exit_reason": "TAKE_PROFIT",
  "confidence": 0.75,
  "status": "closed"
}
```

### Single Exchange vs Multi-Exchange

**Single Exchange**: Each bot writes to its own log file:
- `logs/trades/hibachi.json`
- `logs/trades/lighter.json`
- `logs/trades/extended.json`

**Multi-Exchange (Unified Paper Trade)**: The orchestration script (`scripts/unified_paper_trade.py`) manages positions across all exchanges simultaneously, with:
- Shared learning state in `logs/shared_insights.json`
- Combined decision making via single LLM call
- Per-exchange position tracking

### Log Rotation

Trade logs automatically rotate after 1,000 entries:
- Active log: `{exchange}.json`
- Archive: `{exchange}_{timestamp}.json`

**Implementation**: `trade_tracker.py`

---

## Project Structure

```
hopium-agents/
├── hibachi_agent/           # Hibachi DEX bot
├── lighter_agent/           # Lighter DEX bot
├── extended_agent/          # Extended DEX bot (Python 3.11+)
├── paradex_agent/           # Paradex bot
├── llm_agent/               # Shared LLM infrastructure
│   ├── llm/                 # Model client, prompt formatting
│   ├── data/                # Market data fetchers
│   ├── prompts_archive/     # Prompt versions (v1-v9+)
│   ├── self_learning.py     # Per-bot learning
│   └── shared_learning.py   # Cross-bot insights
├── dexes/                   # Exchange SDK wrappers
├── scripts/                 # Utilities and standalone scripts
├── docs/                    # Detailed documentation
├── research/                # Experiments and analysis
└── logs/                    # Trade logs (gitignored)
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/STRATEGIES.md](docs/STRATEGIES.md) | Complete strategy documentation |
| [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) | All data sources and APIs |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture |
| [CLAUDE.md](CLAUDE.md) | AI agent context file |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines |
| [Project_Analysis.md](Project_Analysis.md) | Trade data analysis |
| [research/Learnings.md](research/Learnings.md) | Strategy learnings and evolution |

---

## Testing Results

**16,803 trades** across 5 exchanges. **50+ strategy iterations**. Oct 2025 - Jan 2026.

### Key Findings

#### 1. LLM Confidence is Poorly Calibrated

| Confidence | Expected WR | Actual WR | Gap |
|------------|-------------|-----------|-----|
| 0.6 | 60% | 46.2% | -14% |
| 0.7 | 70% | 44.7% | -25% |
| 0.8 | 80% | 44.2% | -36% |
| 0.9 | 90% | 51.7% | -38% |

**Implication**: Don't size positions based on LLM confidence. The 0.8 confidence bucket actually won *less often* than 0.7.

#### 2. Win Rate ≠ Profitability

58% win rate can still lose money. Why?
- Fees eat small wins (0.02% taker = 0.1% win becomes 0.06%)
- Average loss > average win ($0.25 loss vs $0.15 win)
- Funding rates cost money (paid every 8 hours)

**Focus on**: Risk-reward ratio, not win rate. A 30% win rate is profitable if winners are 3x losers.

#### 3. What Works

| Finding | Evidence |
|---------|----------|
| 5-signal scoring (RSI+MACD+Vol+PA+OI) | +22.3% in 17 days (Alpha Arena) |
| Hard exit rules (+2%/-1.5%, 2h min) | Major improvement over LLM exits |
| SHORT bias on Lighter/Extended | SHORT WR: 49.4% vs LONG: 41.8% |
| 2-5 positions max | Reduces overtrading |
| Tight Grid MM spreads (1.5 bps) | v8 profitable at +$1.81/$10k |

#### 4. What Doesn't Work

| Approach | Why It Failed |
|----------|---------------|
| Wider Grid MM spreads | v2-v4 all worse than v1 |
| Deep42 for exit decisions | Causes early exits on winners |
| Sizing up on high confidence | 0.8 conf = 44% actual WR |
| Mean reversion (RSI < 30 = buy) | Crypto trends hard |
| High-frequency scalping | Fees destroy profits |

### Detailed Analysis

- **[Project_Analysis.md](Project_Analysis.md)** - Complete trade data, strategy iterations
- **[research/Learnings.md](research/Learnings.md)** - Core principles, exchange-specific findings

---

## License

MIT
