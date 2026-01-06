# Hopium Agents

LLM trading agents for perpetual DEXs. Feed quant data (funding, OI, volume, RSI, MACD), let the model decide.

---

## Setup

```bash
git clone https://github.com/[your-username]/hopium-agents.git
cd hopium-agents
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your keys:
```bash
OPEN_ROUTER=your_openrouter_key
CAMBRIAN_API_KEY=your_cambrian_key

# Pick your exchange
HIBACHI_PUBLIC_KEY=...
HIBACHI_PRIVATE_KEY=...
# or
LIGHTER_PUBLIC_KEY=...
LIGHTER_PRIVATE_KEY=...
```

---

## Running a Bot

```bash
# Hibachi (recommended, has most strategy options)
python3 -m hibachi_agent.bot_hibachi --live --strategy F --interval 600

# Lighter
python3 -m lighter_agent.bot_lighter --live --interval 300

# Extended (requires Python 3.11+)
python3.11 -m extended_agent.bot_extended --live --strategy D --interval 300

# Grid MM on Paradex
python3 scripts/grid_mm_live.py
```

Options:
- `--dry-run`: No real trades, just log decisions
- `--live`: Real trading
- `--strategy X`: Pick a strategy (see below)
- `--interval N`: Seconds between decision cycles

---

## Strategies

**Full documentation: [docs/STRATEGIES.md](docs/STRATEGIES.md)**

Quick reference:

| Flag | Strategy | What It Does |
|------|----------|--------------|
| F | Self-improving | Learns from trade outcomes. Auto-blocks losing symbol/direction combos. |
| D | Pairs trade | Long ETH + Short BTC (or vice versa). LLM picks which to long. |
| G | Low-liq hunter | Targets volatile pairs (HYPE, PUMP, etc). Trailing stops. |
| A | Hard exits | +4% TP, -2% SL, 2h max hold. Overrides LLM. |
| C | Copy whale | Mirrors 0x023a wallet positions proportionally. |

### How the Bot Decides

1. Fetches market data (price, RSI, MACD, volume, funding, OI)
2. Builds prompt with data + strategy context
3. Queries LLM (Qwen via OpenRouter)
4. Validates decisions, executes trades
5. Monitors for exit conditions

The **strategy** controls what goes into the prompt and how exits are handled.

### Active Prompt: v9_qwen_enhanced

Based on Alpha Arena Season 1 winner (+22.3% in 17 days).

**Signal scoring:** RSI + MACD + Volume + Price Action + OI confluence.
**Rule:** Score >= 3.0 required to trade.
**Philosophy:** 30% win rate is fine if winners are 3x losers.

File: `llm_agent/prompts_archive/v9_qwen_enhanced.txt`

### Grid Market Making

`scripts/grid_mm_live.py` runs on Paradex:
- `spread_bps`: Spread in basis points (default 1.5)
- `pause_duration`: Seconds to pause after fills (default 15)
- `inventory_limit`: Max position as % of account (default 25%)

---

## Data Sources

The bots fetch:
- Price, volume, funding rate from exchange APIs
- RSI, MACD, EMA calculated locally
- Open interest from exchange
- Deep42 sentiment from Cambrian API (optional)

---

## Logs

All logs go to `logs/`:
- `logs/hibachi_bot.log` - Bot decisions and errors
- `logs/trades/hibachi.json` - Trade history
- `logs/strategy_switches.log` - Strategy change history

---

## Project Structure

```
hopium-agents/
├── hibachi_agent/          # Hibachi DEX bot
├── lighter_agent/          # Lighter DEX bot
├── extended_agent/         # Extended DEX bot
├── paradex_agent/          # Paradex bot
├── llm_agent/              # Shared LLM code
│   ├── llm/                # Model client, prompt formatting
│   └── prompts_archive/    # Prompt versions (v1-v9)
├── dexes/                  # Exchange SDK wrappers
├── scripts/                # Utility scripts
└── logs/                   # Trade logs (gitignored)
```

---

## Docs

| Doc | What it is |
|-----|------------|
| [docs/STRATEGIES.md](docs/STRATEGIES.md) | Detailed strategy documentation (parameters, files, how they work) |
| [CLAUDE.md](CLAUDE.md) | For AI agents working on this codebase |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute |
| [Project_Analysis.md](Project_Analysis.md) | My testing history, what worked, what didn't |
| [research/Learnings.md](research/Learnings.md) | Strategy learnings |

---

## My Testing Results

I've run 16,803 trades across 50+ strategy iterations. Key findings:
- 0.8 LLM confidence = 44% actual win rate (don't trust confidence)
- Hard exit rules beat LLM discretion on exits
- SHORT outperforms LONG on Lighter/Extended
- BCH, BNB, ZEC are consistent losers

Full analysis: [Project_Analysis.md](Project_Analysis.md)

---

## License

MIT
