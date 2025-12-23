# Hopium Agents

Autonomous LLM-powered trading agents. An experiment in AgentFi - letting AI make trading decisions based on quantitative market data.

**This is experimental software.** I run these agents with real money to learn what works and what doesn't. It may make money, it may lose money. The logs and trade history are here for education, not as financial advice.

## What This Is

Trading agents that feed an LLM (DeepSeek/Qwen/Claude) market data and let it decide: BUY, SELL, CLOSE, or HOLD. No hard-coded rules - the LLM interprets the data and makes autonomous decisions.

The system is exchange-agnostic. You can connect it to any DEX or CEX by implementing a simple adapter.

## Data Sources

The prompt is just text - you can feed the LLM any data you can fetch. Here's what's possible and what we've actually used:

**What we feed the LLM (currently using):**
- Funding rates - long/short bias from perp funding
- Open Interest - total open positions (market leverage)
- Volume - 24h trading volume
- RSI, MACD, EMA/SMA - technical indicators (calculated from OHLCV)
- Order book - bid/ask depth and imbalance
- Price - current spot/mark price
- Deep42 sentiment - AI market intelligence from Cambrian Network

**What you could add:**
- Any API data you can fetch (social sentiment, on-chain metrics, news, etc.)
- Any calculation you can run on OHLCV data
- Any external signal or indicator

The prompt is the interface. If you can turn it into text, the LLM can use it.

## Connected Exchanges

This system works with any exchange. Here are the ones we've connected and actively run strategies on:

| Exchange | Agent Directory | Status |
|----------|-----------------|--------|
| Hibachi | `hibachi_agent/` | Active |
| Lighter | `lighter_agent/` | Active |
| Lighter | `extended_agent/` | Active |
| Pacifica | `pacifica_agent/` | Paused |

Each agent uses the same centralized strategy system in `llm_agent/`. The exchange-specific code just handles data fetching and order execution.

## Quick Start

```bash
# Clone
git clone https://github.com/[your-username]/hopium-agents.git
cd hopium-agents

# Install
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run an agent
python3 -m hibachi_agent.bot_hibachi --live --interval 600
python3 -m lighter_agent.bot_lighter --live --interval 300
python3 -m extended_agent.bot_extended --live --strategy C --interval 300
```

## Project Structure

```
hopium-agents/
├── hibachi_agent/      # Exchange adapter
├── lighter_agent/      # Exchange adapter
├── extended_agent/     # Exchange adapter
├── pacifica_agent/     # Exchange adapter
├── llm_agent/          # Shared strategy engine (all agents use this)
│   ├── llm/            # LLM integration
│   ├── data/           # Market data fetchers & indicators
│   └── prompts_archive/# Historical prompt versions
├── dexes/              # Exchange SDKs
├── research/           # Research and experiments
└── logs/               # Trade logs (gitignored)
```

## How It Works

Every N minutes (configurable):

1. Fetch market data from exchange
2. Calculate indicators (RSI, MACD, EMA, funding, OI)
3. Query Deep42 for macro sentiment (optional)
4. Send everything to LLM with current positions
5. LLM returns decision + reasoning
6. Execute the trade

The LLM prompt is the strategy. We've iterated through 17 prompt versions so far - from simple technicals-only to complex multi-timeframe analysis. See `logs/strategy_switches.log` for the evolution.

## Strategy History

We track every strategy change in `logs/strategy_switches.log`. Some highlights:

- **deep42-v1**: First Deep42 integration
- **technicals-only-v1**: Removed Deep42 "risk-off" panic that was killing winners
- **hard-exit-rules-v1**: Added forced exits at +2%/-1.5% to override LLM discretion
- **aggressive-selective-v1**: Quality over quantity - 2-5 positions max
- **deep42-bias-v7**: Current - Dynamic Deep42 directional bias

## Cambrian Integration

We use [Cambrian Network](https://cambrian.network) for AI-powered market intelligence:

- **Deep42**: Natural language market queries ("Is the market risk-on or risk-off?")
- **Risk Engine**: Monte Carlo liquidation probability (gates risky trades)
- **OHLCV API**: Historical candle data for backtesting

## Configuration

Required in `.env`:

```bash
# LLM (pick one)
DEEPSEEK_API_KEY=your_key
# or CLAUDE_API_KEY, OPEN_ROUTER, etc.

# Cambrian (optional but recommended)
CAMBRIAN_API_KEY=your_key

# Exchange credentials (for the agent you're running)
# See .env.example for full list
```

## Agent Commands

```bash
# Check what's running
ps aux | grep -E "(hibachi|lighter|extended|pacifica)_agent"

# View logs
tail -f logs/hibachi_bot.log
tail -f logs/lighter_bot.log
tail -f logs/extended_bot.log

# Stop an agent
pkill -f "hibachi_agent.bot_hibachi"

# Start in background
nohup python3 -u -m hibachi_agent.bot_hibachi --live --interval 600 > logs/hibachi_bot.log 2>&1 &
```

## Logs

The `logs/` directory contains my personal trading logs. They're gitignored but worth mentioning:

1. **Educational value**: Real LLM decisions and outcomes
2. **Not for copying**: My trades, my risk tolerance
3. **Strategy evolution**: `logs/strategy_switches.log` shows iteration history

## For AI Agents

If you're an AI agent (Claude, GPT, etc.) working on this codebase, see [CLAUDE.md](CLAUDE.md).

## Disclaimer

This is an experiment in AgentFi - exploring what happens when you let LLMs make trading decisions. It may make money, it may lose money. I run it to learn, not because it's profitable.

- Don't trade money you can't afford to lose
- Don't copy trades or strategies directly
- Past performance means nothing
- Not financial advice

## License

MIT
