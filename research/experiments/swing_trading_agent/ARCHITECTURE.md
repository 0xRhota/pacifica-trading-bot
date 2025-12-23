# Swing Trading Bot - Complete Architecture

## Overview Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SWING TRADING BOT                                    │
│                    (bot_swing.py - Main Loop)                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EVERY 30 MINUTES                                   │
│                        (CHECK_INTERVAL_SECONDS)                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌──────────────────────────────┐   ┌──────────────────────────────┐
│      HIBACHI DEX             │   │      EXTENDED DEX            │
│      (Solana)                │   │      (Starknet)              │
└──────────────────────────────┘   └──────────────────────────────┘
                    │                               │
                    ▼                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PER-DEX CYCLE                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 1: FETCH DATA                                                   │   │
│  │ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │   │
│  │ │   OHLCV     │  │  Funding    │  │   Open      │  │  Account    │  │   │
│  │ │  Candles    │  │   Rates     │  │ Interest    │  │  Balance    │  │   │
│  │ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 2: CALCULATE INDICATORS                                         │   │
│  │ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │   │
│  │ │    RSI      │  │    MACD     │  │   SMA 20    │  │   SMA 50    │  │   │
│  │ │  (14-period)│  │ (12,26,9)   │  │             │  │             │  │   │
│  │ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 3: CHECK OPEN POSITIONS (Hard Exit Rules - NO AI)              │   │
│  │                                                                      │   │
│  │ For each position:                                                   │   │
│  │   • P/L >= +15%? → FORCE CLOSE (Take Profit)                        │   │
│  │   • P/L <= -5%?  → FORCE CLOSE (Stop Loss)                          │   │
│  │   • Hold > 96h?  → FORCE CLOSE (Max Hold)                           │   │
│  │   • Trend reversed? (SMA + MACD) → FORCE CLOSE                      │   │
│  │   • Hold < 4h & LLM wants close? → BLOCK (Min Hold)                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 4: LLM DECISION (AI - Entry/Exit Decisions)                    │   │
│  │                                                                      │   │
│  │ IF positions < MAX (3):                                              │   │
│  │   ┌───────────────────────────────────────────────────────────────┐ │   │
│  │   │            FORMAT PROMPT FOR LLM                               │ │   │
│  │   │   • Market data table (all indicators)                        │ │   │
│  │   │   • Current positions                                         │ │   │
│  │   │   • Account balance                                           │ │   │
│  │   │   • Recent trade history                                      │ │   │
│  │   │   • Strategy instructions (v5_swing_trading.txt)              │ │   │
│  │   └───────────────────────────────────────────────────────────────┘ │   │
│  │                              │                                       │   │
│  │                              ▼                                       │   │
│  │   ┌───────────────────────────────────────────────────────────────┐ │   │
│  │   │            QUERY LLM (DeepSeek or Qwen)                       │ │   │
│  │   │   • Temperature: 0.1 (deterministic)                          │ │   │
│  │   │   • Max tokens: 500                                           │ │   │
│  │   └───────────────────────────────────────────────────────────────┘ │   │
│  │                              │                                       │   │
│  │                              ▼                                       │   │
│  │   ┌───────────────────────────────────────────────────────────────┐ │   │
│  │   │            PARSE LLM RESPONSE                                  │ │   │
│  │   │   • Extract: TOKEN, DECISION, CONFIDENCE, REASON              │ │   │
│  │   │   • Validate: Symbol exists, confidence > threshold           │ │   │
│  │   └───────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 5: EXECUTE TRADES                                               │   │
│  │                                                                      │   │
│  │ For each LLM decision:                                               │   │
│  │   • BUY → Open LONG position                                        │   │
│  │   • SELL → Open SHORT position                                      │   │
│  │   • CLOSE → Close existing position                                 │   │
│  │                                                                      │   │
│  │ Via DEX SDK:                                                         │   │
│  │   • Hibachi: HMAC-authenticated REST API                            │   │
│  │   • Extended: Starknet signed transactions                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 6: LOG & TRACK                                                  │   │
│  │   • TradeTracker: Record entry/exit prices, timestamps              │   │
│  │   • Logs: logs/swing_trading_bot.log                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                         WAIT 30 MINUTES → REPEAT
```

---

## Data Sources

### 1. Price/OHLCV Data

| Source | Used For | Endpoint |
|--------|----------|----------|
| **Binance Futures** | Historical candles (15m) | `https://fapi.binance.com/fapi/v1/klines` |
| **Hibachi API** | Current price, funding | `https://data-api.hibachi.xyz` |
| **Extended API** | Current price, positions | Extended Starknet API |

**Why Binance for candles?** Hibachi doesn't provide historical OHLCV data. Since Hibachi trades the same assets (BTC, ETH, SOL), Binance Futures prices are a reliable proxy.

### 2. Funding Rates

| Source | Used For |
|--------|----------|
| **Hibachi API** | Per-symbol funding rate |
| **Extended API** | Per-symbol funding rate |

### 3. Open Interest

| Source | Used For |
|--------|----------|
| **OI Data Fetcher** | Market participation levels |

### 4. Account Data

| Source | Data |
|--------|------|
| **Hibachi SDK** | Balance, positions |
| **Extended SDK** | Balance, positions |

---

## Technical Indicators Calculated

All calculated using the `ta` library in `indicator_calculator.py`:

| Indicator | Period | Purpose |
|-----------|--------|---------|
| **RSI** | 14 | Momentum - overbought (>70) / oversold (<30) |
| **MACD** | 12, 26, 9 | Trend strength and crossovers |
| **SMA 20** | 20 | Short-term trend |
| **SMA 50** | 50 | Medium-term trend |
| **Bollinger Bands** | 20, 2σ | Volatility |
| **Volume** | 24h sum | Market activity |

**Trend Confirmation Rule:**
- LONG only if: `SMA20 > SMA50`
- SHORT only if: `SMA20 < SMA50`

---

## AI Touchpoints

### 1. LLM for Entry Decisions

**When:** Every 30-minute cycle, IF positions < 3

**Model Options:**
- `deepseek-chat` (default) - Via DeepSeek API
- `qwen-max` - Via OpenRouter

**Prompt Contains:**
```
1. Strategy instructions (v5_swing_trading.txt)
2. Market data table:
   - Symbol, Price, 24h Volume
   - RSI, MACD, SMA20, SMA50
   - Funding rate, Open Interest
3. Current open positions
4. Account balance
5. Recent trade history
6. Recently closed symbols (to avoid re-entry)
```

**LLM Response Format:**
```
TOKEN: SOL
DECISION: BUY SOL
CONFIDENCE: 0.75
REASON: RSI 38 oversold, MACD bullish crossover, SMA20 > SMA50 uptrend
```

### 2. Hard Rules Override LLM (No AI)

**Exit rules are NOT AI-driven.** They are hard-coded:

| Rule | Condition | Action |
|------|-----------|--------|
| Take Profit | P/L >= +15% | Force close |
| Stop Loss | P/L <= -5% | Force close |
| Max Hold | Time > 96h | Force close |
| Trend Reversal | SMA + MACD signal | Force close |
| Min Hold | Time < 4h | Block LLM close |

**Why?** Research showed LLM is too risk-averse and closes winners too early.

---

## Complete Data Flow

```
1. INITIALIZATION
   ├── Load .env (API keys)
   ├── Initialize HibachiSDK (Solana DEX)
   ├── Initialize ExtendedSDK (Starknet DEX)
   ├── Initialize LLMTradingAgent (DeepSeek/Qwen)
   └── Initialize SwingExitRules (15% TP, 5% SL)

2. EVERY 30 MINUTES (per DEX):

   2a. FETCH DATA
       ├── Hibachi/Extended API → Get available markets
       ├── Binance Futures → Get 15m OHLCV candles (100 bars)
       ├── DEX API → Get current price, funding rate
       └── DEX API → Get open positions, account balance

   2b. CALCULATE INDICATORS
       └── indicator_calculator.py:
           ├── RSI(14)
           ├── MACD(12, 26, 9)
           ├── SMA(20), SMA(50)
           └── Bollinger Bands

   2c. CHECK HARD EXIT RULES (swing_exit_rules.py)
       └── For each open position:
           ├── Calculate P/L %
           ├── Calculate hold time
           └── Check: TP hit? SL hit? Max hold? Trend reversed?
               └── If yes → Execute CLOSE (bypass LLM)

   2d. LLM DECISION (if positions < 3)
       ├── Format prompt (prompt_formatter.py)
       │   ├── Market data table
       │   ├── Open positions
       │   ├── Account balance
       │   └── Strategy instructions
       ├── Query LLM (model_client.py)
       │   └── DeepSeek API or OpenRouter (Qwen)
       └── Parse response (response_parser.py)
           └── Extract: symbol, action, confidence, reason

   2e. EXECUTE TRADES
       ├── Validate decision (symbol exists, not already positioned)
       ├── Map BUY→LONG, SELL→SHORT
       └── Execute via DEX SDK:
           ├── Hibachi: POST /order/create with HMAC signature
           └── Extended: Starknet signed transaction

   2f. RECORD TRADE
       └── trade_tracker.py:
           ├── Save entry price, timestamp
           ├── Track P/L
           └── Write to logs/trades/{dex}.json

3. WAIT 30 MINUTES → REPEAT
```

---

## File Structure

```
swing_trading_agent/
├── __init__.py
├── config.py                 # Strategy parameters (15% TP, 5% SL, etc.)
├── swing_exit_rules.py       # Hard exit rules (override LLM)
├── bot_swing.py              # Main bot loop
└── ARCHITECTURE.md           # This file

llm_agent/
├── llm/
│   ├── model_client.py       # DeepSeek/OpenRouter API client
│   ├── prompt_formatter.py   # Format market data for LLM
│   ├── response_parser.py    # Parse LLM decisions
│   └── trading_agent.py      # LLM orchestration
├── data/
│   ├── indicator_calculator.py  # RSI, MACD, SMA
│   └── macro_fetcher.py      # Fear & Greed, etc.
└── prompts_archive/
    └── v5_swing_trading.txt  # Strategy prompt

hibachi_agent/
├── data/
│   ├── hibachi_fetcher.py    # Fetch from Hibachi + Binance
│   ├── hibachi_aggregator.py # Combine all data sources
│   └── binance_proxy.py      # Binance Futures candle proxy
└── execution/
    └── hibachi_executor.py   # Execute trades on Hibachi

extended_agent/
├── data/
│   ├── extended_fetcher.py   # Fetch from Extended
│   └── extended_aggregator.py
└── execution/
    └── extended_executor.py  # Execute trades on Extended

dexes/
├── hibachi/
│   └── hibachi_sdk.py        # Hibachi REST API + HMAC auth
└── extended/
    └── extended_sdk.py       # Extended Starknet SDK
```

---

## Configuration

### swing_trading_agent/config.py

```python
# Risk Management (3:1 R/R)
TAKE_PROFIT_PCT = 15.0      # Close at +15%
STOP_LOSS_PCT = 5.0         # Close at -5%

# Hold Time
MIN_HOLD_HOURS = 4.0        # Don't close before 4 hours
MAX_HOLD_HOURS = 96.0       # Close after 4 days

# Position Limits
MAX_POSITIONS = 3           # Quality over quantity
POSITION_SIZE_PCT = 0.05    # 5% of capital per trade

# Timing
CHECK_INTERVAL_SECONDS = 1800  # 30 minutes
```

---

## API Keys Required (.env)

```bash
# LLM
DEEPSEEK_API_KEY=sk-...      # DeepSeek Chat
OPEN_ROUTER=sk-or-v1-...     # OpenRouter (for Qwen)

# Data
CAMBRIAN_API_KEY=...         # Macro context

# Hibachi (Solana)
HIBACHI_PUBLIC_KEY=...
HIBACHI_PRIVATE_KEY=...
HIBACHI_ACCOUNT_ID=...

# Extended (Starknet)
EXTENDED_API_KEY=...
EXTENDED_STARK_PRIVATE_KEY=...
EXTENDED_STARK_PUBLIC_KEY=...
EXTENDED_VAULT=...
```

---

## Key Decisions

### Why Hard Exit Rules Override LLM?

Research showed:
- LLM is too risk-averse
- Closes winners at +0.5% instead of letting them run
- Holds losers hoping for recovery
- **Solution:** Hard rules force +15% TP and -5% SL regardless of LLM opinion

### Why 3:1 R/R?

Math:
- With 15% TP and 5% SL, you only need **25% win rate** to break even
- Previous bot needed 68% win rate (impossible with LLM)
- This is mathematically more forgiving

### Why 4-Hour Minimum Hold?

Research on winning wallet:
- 90.2% of profitable trades held 4+ hours
- Average hold: 93.5 hours (3.9 days)
- Scalping doesn't work at small scale

### Why Two DEXs?

- Diversification across chains (Solana + Starknet)
- Different liquidity pools
- **Qwen recommended:** Consider focusing on single DEX first

---

## Monitoring

### Logs
- `logs/swing_trading_bot.log` - All activity
- `logs/trades/hibachi_swing.json` - Hibachi trades
- `logs/trades/extended_swing.json` - Extended trades

### Key Metrics to Track
- Win rate (target: >25%)
- Average P/L per trade
- Time held distribution
- Exit reason breakdown (TP/SL/trend/max hold)
- Balance over time
