# Moon Dev AI Trading Agent - Data Pipeline Deep Dive

## Executive Summary

Moon Dev's trading agent is a **multi-exchange, multi-AI consensus system** with a clear three-stage data pipeline:
1. **Collection**: Fetch OHLCV from Birdeye (Solana), HyperLiquid, or Aster APIs
2. **Processing**: Convert to DataFrame, calculate indicators with pandas_ta
3. **Prompt Construction**: Format DataFrame as readable text for LLM consensus voting

The system uses 6 AI models in parallel (or 1 for speed) to vote on trading decisions.

---

## 1. DATA COLLECTION CODE

### 1.1 Collection Entry Point: `ohlcv_collector.py`

**File**: `/src/data/ohlcv_collector.py`

**Main Function**: `collect_token_data()`
```python
def collect_token_data(token, days_back=3, timeframe='15m', exchange="SOLANA"):
    # Dispatches to correct data source based on exchange type
    # Returns: pandas DataFrame with OHLCV data
    
    # Dispatching logic:
    if exchange == "HYPERLIQUID":
        data = hl.get_data(symbol=token, timeframe=timeframe, bars=bars_needed)
    elif exchange == "ASTER":
        data = hl.get_data(...)  # Uses HyperLiquid SDK
    else:  # "SOLANA"
        data = n.get_data(token, days_back, timeframe)  # Uses Birdeye API
```

**Key Details**:
- Converts timeframe format: '1H' → '1h', '1D' → '1d' for HyperLiquid compatibility
- Calculates bars needed: `days_back × bars_per_day[timeframe]`
  - 1m: 1440/day, 15m: 96/day, 1H: 24/day, 1D: 1/day
- Default: 3 days @ 15m = 288 bars, 3 days @ 1H = 72 bars
- **Caches data locally** to `temp_data/{token}_latest.csv` (or `data/` if `SAVE_OHLCV_DATA=True`)
- Saves all 6 models' responses to files for auditing

### 1.2 Solana/Birdeye: `nice_funcs.py`

**API**: Birdeye REST (`https://public-api.birdeye.so/defi/ohlcv`)

**Function**: `get_data(address, days_back_4_data, timeframe)`
```python
# Build request URL with time range
url = f"https://public-api.birdeye.so/defi/ohlcv?address={address}&type={timeframe}&time_from={time_from}&time_to={time_to}"

# API Response format (raw JSON):
{
    "data": {
        "items": [
            {
                "unixTime": 1234567890,
                "o": 0.1234,      # open
                "h": 0.1235,      # high
                "l": 0.1233,      # low
                "c": 0.1234,      # close
                "v": 1000000      # volume
            }
        ]
    }
}

# Convert to DataFrame:
processed_data = [{
    'Datetime (UTC)': datetime.utcfromtimestamp(item['unixTime']),
    'Open': item['o'],
    'High': item['h'],
    'Low': item['l'],
    'Close': item['c'],
    'Volume': item['v']
} for item in items]
```

**Caching**:
```python
# Check temp cache first
temp_file = f"temp_data/{address}_latest.csv"
if os.path.exists(temp_file):
    return pd.read_csv(temp_file)
# If not cached, fetch from API and save
df.to_csv(temp_file)
```

**Data Padding**:
- If fewer than 40 bars, **replicates first bar** to reach minimum
- Filters out future-dated rows

**Error Handling**:
- HTTP 401 → Missing `BIRDEYE_API_KEY` in .env
- Returns empty DataFrame on failure

---

### 1.3 HyperLiquid: `nice_funcs_hyperliquid.py`

**API**: HyperLiquid REST (`https://api.hyperliquid.xyz/info`)

**Key Request Format**:
```python
request_payload = {
    "type": "candleSnapshot",
    "req": {
        "coin": "BTC",              # Symbol
        "interval": "15m",          # Timeframe
        "startTime": start_ts,      # Milliseconds epoch
        "endTime": end_ts,          # Milliseconds epoch
        "limit": 5000               # Max batch size
    }
}

response = requests.post(
    'https://api.hyperliquid.xyz/info',
    headers={'Content-Type': 'application/json'},
    json=request_payload,
    timeout=10
)
```

**API Response Format**:
```python
# Raw response is array of candles:
[
    {
        "t": 1234567890000,  # timestamp in ms
        "o": "45000",        # open (string!)
        "h": "45100",        # high
        "l": "44900",        # low
        "c": "45050",        # close
        "v": "1000.5"        # volume
    },
    ...
]
```

**Data Processing**:
```python
def _process_data_to_df(snapshot_data):
    """Convert raw HyperLiquid API response to DataFrame"""
    data = []
    for snapshot in snapshot_data:
        timestamp = datetime.datetime.utcfromtimestamp(snapshot['t'] / 1000)
        data.append([
            timestamp,
            float(snapshot['o']),  # Convert strings to floats
            float(snapshot['h']),
            float(snapshot['l']),
            float(snapshot['c']),
            float(snapshot['v'])
        ])
    return pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
```

**Timestamp Handling**:
- Detects **timestamp offset** between API and local system
- Adjusts all timestamps if mismatch detected
- Ensures data alignment across multiple calls

**Time Window Calculation**:
```python
end_time = datetime.datetime.utcnow()
start_time = end_time - timedelta(days=60)  # Fetch up to 60 days, then slice
bars = min(bars, MAX_ROWS)  # Max 5000 bars per HyperLiquid limit
```

**Retry Logic**:
- MAX_RETRIES = 3
- Timeout = 10 seconds per request
- Sleeps 1 second between retries

---

### 1.4 Aster DEX: `nice_funcs_aster.py`

Uses AsterAPI wrapper library (requires local Aster-Dex-Trading-Bots import)

```python
# Initialize (global instance)
api = AsterAPI(ASTER_API_KEY, ASTER_API_SECRET)
funcs = AsterFuncs(api)

# Get symbol precision for proper rounding
symbol_precision = api.get_exchange_info()  # Returns price/qty decimals

# Get current price
midpoint = (api.get_ask_bid(symbol)[0] + api.get_ask_bid(symbol)[1]) / 2
```

---

## 2. DATA PROCESSING PIPELINE

### 2.1 DataFrame Structure After Collection

**Standard DataFrame**:
```
Index | timestamp           | open   | high   | low    | close  | volume
------|------------------|--------|--------|--------|--------|----------
0     | 2025-01-01 00:00 | 0.1234 | 0.1235 | 0.1233 | 0.1234 | 1000000
1     | 2025-01-01 01:00 | 0.1234 | 0.1235 | 0.1233 | 0.1234 | 1000000
...
```

---

### 2.2 Technical Indicator Calculation

**Function**: `add_technical_indicators(df)` in `nice_funcs_hyperliquid.py`

Uses **pandas_ta** library for all calculations:

```python
import pandas_ta as ta

# Simple Moving Averages (SMA)
df['sma_20'] = ta.sma(df['close'], length=20)
df['sma_50'] = ta.sma(df['close'], length=50)

# Relative Strength Index (RSI)
df['rsi'] = ta.rsi(df['close'], length=14)

# MACD (Moving Average Convergence Divergence)
macd = ta.macd(df['close'])  # Returns df with MACD, signal, histogram
df = pd.concat([df, macd], axis=1)

# Bollinger Bands
bbands = ta.bbands(df['close'])  # Returns BBL, BBM, BBU, BBB, BBP
df = pd.concat([df, bbands], axis=1)
```

**Indicator Formulas** (from pandas_ta defaults):
- **SMA**: Simple average of last N periods
- **RSI(14)**: Relative strength = 100 × RS / (1 + RS), where RS = avg_up / avg_down
- **MACD**: 12-period EMA - 26-period EMA
- **BBands**: 20-period SMA ± (std_dev × 2)

**Also calculated in nice_funcs.py for Solana**:
```python
df['MA20'] = ta.sma(df['Close'], length=20)
df['MA40'] = ta.sma(df['Close'], length=40)
df['RSI'] = ta.rsi(df['Close'], length=14)
df['Price_above_MA20'] = df['Close'] > df['MA20']
df['Price_above_MA40'] = df['Close'] > df['MA40']
df['MA20_above_MA40'] = df['MA20'] > df['MA40']
```

---

### 2.3 Error Handling in Processing

```python
try:
    # Calculate indicators
    numeric_cols = ['open', 'high', 'low', 'close', 'volume']
    df[numeric_cols] = df[numeric_cols].astype('float64')  # Ensure floats
    
    df = add_technical_indicators(df)
except Exception as e:
    print(f"❌ Error: {e}")
    return df  # Return unprocessed data if indicators fail
```

**Data Validation**:
- Type checking: convert strings to float64
- Verify non-empty DataFrame before processing
- Print first 5 rows for debugging

---

## 3. PROMPT CONSTRUCTION FOR LLM

### 3.1 Swarm Mode Prompt Format

**File**: `trading_agent.py` lines 530-577

**Function**: `_format_market_data_for_swarm(token, market_data)`

```python
# Format market data as readable text for LLM
formatted = f"""
TOKEN: {token}
TIMEFRAME: {DATA_TIMEFRAME} bars
TOTAL BARS: {len(market_data)}
DATE RANGE: {market_data.index[0]} to {market_data.index[-1]}

RECENT PRICE ACTION (Last 10 bars):
{market_data.tail(10).to_string()}

FULL DATASET:
{market_data.to_string()}
"""

# If strategy signals available, append:
if isinstance(market_data, dict) and 'strategy_signals' in market_data:
    formatted += f"\n\nSTRATEGY SIGNALS:\n{json.dumps(market_data['strategy_signals'], indent=2)}"
```

**Output to LLM**:
The entire DataFrame is converted to string via `.to_string()`:
```
    timestamp     open      high       low     close      volume    sma_20    rsi
0  2025-01-01   0.1234    0.1235    0.1233   0.1234   1000000    0.1230     55
1  2025-01-01   0.1234    0.1235    0.1233   0.1234   1000000    0.1231     56
...
```

---

### 3.2 System Prompt for Swarm Voting

**File**: `trading_agent.py` lines 245-261

```python
SWARM_TRADING_PROMPT = """You are an expert cryptocurrency trading AI analyzing market data.

CRITICAL RULES:
1. Your response MUST be EXACTLY one of these three words: Buy, Sell, or Do Nothing
2. Do NOT provide any explanation, reasoning, or additional text
3. Respond with ONLY the action word
4. Do NOT show your thinking process or internal reasoning

Analyze the market data below and decide:

- "Buy" = Strong bullish signals, recommend opening/holding position
- "Sell" = Bearish signals or major weakness, recommend closing position entirely
- "Do Nothing" = Unclear/neutral signals, recommend holding current state unchanged

IMPORTANT: "Do Nothing" means maintain current position (if we have one, keep it; if we don't, stay out)

RESPOND WITH ONLY ONE WORD: Buy, Sell, or Do Nothing"""
```

**Why this design**:
- **Exactly 3 choices**: Simplifies consensus voting (no nuance, just majority wins)
- **No explanation needed**: Faster parallel execution, easier parsing
- **Clear semantics**: Unambiguous action mapping

---

### 3.3 Consensus Calculation from Swarm Votes

**File**: `trading_agent.py` lines 579-641

```python
def _calculate_swarm_consensus(swarm_result):
    """
    Count votes from all models:
    - BUY: strong bullish
    - SELL: bearish/close
    - NOTHING: hold
    """
    votes = {"BUY": 0, "SELL": 0, "NOTHING": 0}
    
    for provider, data in swarm_result["responses"].items():
        if not data["success"]:
            continue
        
        response_text = data["response"].strip().upper()
        
        # Parse one-word response
        if "BUY" in response_text:
            votes["BUY"] += 1
        elif "SELL" in response_text:
            votes["SELL"] += 1
        else:
            votes["NOTHING"] += 1
    
    # Find majority
    majority_action = max(votes, key=votes.get)  # Most votes wins
    majority_count = votes[majority_action]
    total_votes = sum(votes.values())
    
    # Confidence = % of votes for majority action
    confidence = int((majority_count / total_votes) * 100)
    
    return majority_action, confidence, reasoning_summary
```

**Example**:
- 6 models vote: BUY, BUY, SELL, BUY, NOTHING, BUY
- **Majority**: BUY (4 votes)
- **Confidence**: 4/6 = 67%
- **Action**: BUY with 67% confidence

---

## 4. CONFIGURATION SYSTEM

### 4.1 Configuration Sources

**Order of precedence**:
1. **trading_agent.py (top priority)** - Lines 66-177
   - Contains all settings for current run
   - Overrides config.py values
   - Exchange selection (ASTER, HYPERLIQUID, SOLANA)
   - Token lists (SYMBOLS for futures, MONITORED_TOKENS for Solana)
   - AI mode (USE_SWARM_MODE, single model)
   - Position sizing, leverage, stop-loss, take-profit

2. **config.py** - Legacy settings
   - Fallback values
   - Default token lists
   - Exchange defaults

3. **Environment variables** (.env)
   - API keys
   - Private keys
   - RPC endpoints

### 4.2 Key Configuration Variables

```python
# Exchange Selection
EXCHANGE = "ASTER"  # "ASTER", "HYPERLIQUID", or "SOLANA"

# Data Collection Settings
DAYSBACK_4_DATA = 3         # Days of historical data
DATA_TIMEFRAME = '1H'       # Candle timeframe
SAVE_OHLCV_DATA = False     # False = temp only, True = permanent

# AI Mode
USE_SWARM_MODE = True       # True = 6 models, False = 1 model
AI_MODEL_TYPE = 'xai'       # Only if USE_SWARM_MODE = False
AI_MODEL_NAME = None        # Specific model override

# Position Sizing
MAX_POSITION_PERCENTAGE = 90    # % of account to use as margin
LEVERAGE = 9                    # Leverage multiplier (Aster/HyperLiquid only)

# Risk Management
STOP_LOSS_PERCENTAGE = 5.0      # Exit if -5%
TAKE_PROFIT_PERCENTAGE = 5.0    # Exit if +5%
PNL_CHECK_INTERVAL = 5          # Seconds between P&L checks

# Token Lists (exchange-specific)
SYMBOLS = ['BTC', 'ETH', 'SOL']              # For Aster/HyperLiquid
MONITORED_TOKENS = ['9BB6NF...', 'DitHy...'] # For Solana (contract addresses)
```

---

## 5. API SPECIFICATIONS

### 5.1 Birdeye (Solana)

**Endpoint**: `https://public-api.birdeye.so/defi/ohlcv`

**Query Parameters**:
- `address`: Token contract address
- `type`: Timeframe (1m, 3m, 5m, 15m, 30m, 1H, 4H, 8H, 12H, 1D, 3D, 1W)
- `time_from`: Unix timestamp (seconds)
- `time_to`: Unix timestamp (seconds)

**Headers**:
```
X-API-KEY: {BIRDEYE_API_KEY}
```

**Response Rate**: ~0.5s per request (observed ~50ms actual)

**Max Age of Data**: 5 minutes (tested as 0.046% divergence from Pacifica)

---

### 5.2 HyperLiquid

**Endpoint**: `https://api.hyperliquid.xyz/info`

**Request Format** (POST JSON):
```json
{
    "type": "candleSnapshot",
    "req": {
        "coin": "BTC",
        "interval": "15m",
        "startTime": 1234567890000,
        "endTime": 1234567890000,
        "limit": 5000
    }
}
```

**Available Symbols**: BTC, ETH, SOL, ARB, OP, MATIC, etc.

**Available Intervals**: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 5d, 1w, 1month

**Max Batch**: 5000 candles per request

**Response Time**: ~100-200ms

---

### 5.3 Aster DEX

**Library**: Local `Aster-Dex-Trading-Bots` (via `aster_api.py`)

**Authentication**: API key + secret from environment

**Key Methods**:
```python
api.get_ask_bid(symbol)        # (ask, bid)
api.get_orderbook(symbol)      # Full L2 book
api.change_leverage(symbol)    # Set leverage
```

---

## 6. DATA FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────────────┐
│ COLLECTION LAYER                                            │
├─────────────────────────────────────────────────────────────┤
│
│  collect_token_data(token, days_back=3, timeframe='15m')
│  ├─ Check if token in MONITORED_TOKENS or SYMBOLS
│  ├─ Calculate time range: now - 3 days
│  └─ Route by exchange:
│
│      ├─ SOLANA → Birdeye API
│      │  ├─ GET /defi/ohlcv?address={token}&type={tf}&time_from={}&time_to={}
│      │  ├─ Parse response: unixTime, o, h, l, c, v
│      │  ├─ Convert → DataFrame (Datetime, Open, High, Low, Close, Volume)
│      │  ├─ Pad if < 40 rows
│      │  └─ Save to temp_data/{token}_latest.csv
│      │
│      ├─ HYPERLIQUID → HyperLiquid API
│      │  ├─ POST /info with candleSnapshot request
│      │  ├─ Convert timestamps: ms → seconds
│      │  ├─ Parse response array: t, o, h, l, c, v
│      │  ├─ Convert → DataFrame
│      │  └─ Adjust timestamps if offset detected
│      │
│      └─ ASTER → Aster API (via library)
│         ├─ Get order book, mid price, position info
│         └─ (Data fetching varies by operation type)
│
└──────────────┬──────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────┐
│ PROCESSING LAYER                                            │
├─────────────────────────────────────────────────────────────┤
│
│  add_technical_indicators(df)
│  ├─ Type conversion: ensure float64
│  ├─ SMA_20 = ta.sma(close, length=20)
│  ├─ SMA_50 = ta.sma(close, length=50)
│  ├─ RSI_14 = ta.rsi(close, length=14)
│  ├─ MACD = ta.macd(close)
│  └─ BBands = ta.bbands(close)
│
│  Result: DataFrame with OHLCV + 10+ indicator columns
│
└──────────────┬──────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────┐
│ PROMPT CONSTRUCTION LAYER                                   │
├─────────────────────────────────────────────────────────────┤
│
│  _format_market_data_for_swarm(token, df)
│  ├─ Extract key metadata (token, timeframe, row count, date range)
│  ├─ Show last 10 bars: df.tail(10).to_string()
│  ├─ Show full dataset: df.to_string()
│  ├─ (Optional) Append strategy signals as JSON
│  └─ Result: ~2000-5000 char string
│
│  Output format:
│  """
│  TOKEN: 9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump
│  TIMEFRAME: 1H bars
│  TOTAL BARS: 72
│  DATE RANGE: 2025-01-01 00:00:00 to 2025-01-04 00:00:00
│  
│  RECENT PRICE ACTION (Last 10 bars):
│    timestamp     open      high       low     close    volume    sma_20    rsi
│  0 2025-01-03   0.1234    0.1235    0.1233   0.1234   1000000    0.1230     55
│  ...
│  
│  FULL DATASET:
│  [Full 72-row table]
│  """
│
└──────────────┬──────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────┐
│ LLM CONSENSUS LAYER                                         │
├─────────────────────────────────────────────────────────────┤
│
│  SwarmAgent.query(formatted_data, SWARM_TRADING_PROMPT)
│  │
│  ├─ Parallel execution of 3-6 models:
│  │  ├─ DeepSeek Chat
│  │  ├─ Grok-4 Fast Reasoning
│  │  └─ Qwen3 Max
│  │
│  ├─ Each model returns one of: "Buy", "Sell", or "Do Nothing"
│  │
│  └─ Calculate consensus:
│     ├─ Count votes
│     ├─ Majority wins
│     └─ Confidence = (winning_votes / total_votes) × 100%
│
│  Output: {"action": "BUY", "confidence": 67}
│
└──────────────┬──────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────┐
│ EXECUTION LAYER                                             │
├─────────────────────────────────────────────────────────────┤
│
│  handle_exits() / execute_allocations()
│  │
│  ├─ If action == "BUY":
│  │  └─ Call n.ai_entry(token, position_size, leverage=LEVERAGE)
│  │     ├─ On Aster/HyperLiquid: place leveraged order
│  │     └─ On Solana: swap USDC → token via Jupiter
│  │
│  ├─ If action == "SELL":
│  │  └─ If position exists:
│  │     ├─ Call n.limit_sell() or n.market_sell()
│  │     └─ Monitor P&L, exit at stop-loss or take-profit
│  │
│  └─ If action == "DO NOTHING":
│     └─ Hold current position
│
└─────────────────────────────────────────────────────────────┘
```

---

## 7. KEY PATTERNS TO COPY FOR PACIFICA IMPLEMENTATION

### 7.1 Data Collection Pattern

```python
# 1. Fetch OHLCV from API
url = f"https://api.pacifica.fi/api/v1/kline"
params = {
    "symbol": "SOL",
    "interval": "15m",
    "start_time": start_epoch_ms,
    "limit": 288
}
response = requests.get(url, params=params, headers={"X-API-KEY": key})
data = response.json()

# 2. Convert to DataFrame
df = pd.DataFrame(data)
df['Close'] = df['close'].astype(float)
df['Open'] = df['open'].astype(float)
df['High'] = df['high'].astype(float)
df['Low'] = df['low'].astype(float)
df['Volume'] = df['volume'].astype(float)

# 3. Cache locally
df.to_csv(f"temp_data/{symbol}_latest.csv", index=False)

# 4. Add indicators
df['SMA20'] = ta.sma(df['Close'], length=20)
df['RSI'] = ta.rsi(df['Close'], length=14)

# 5. Format for LLM
formatted = f"""
TOKEN: {symbol}
TIMEFRAME: 15m
DATA:
{df.to_string()}
"""

# 6. Query AI
response = llm.chat(formatted)  # "Buy", "Sell", or "Do Nothing"
```

### 7.2 Indicator Calculation Pattern

```python
import pandas_ta as ta

# Standard set (fast execution)
df['sma_20'] = ta.sma(df['close'], length=20)
df['rsi_14'] = ta.rsi(df['close'], length=14)

# Extended set (slower but more info)
df['sma_50'] = ta.sma(df['close'], length=50)
df['macd'] = ta.macd(df['close'])
df['bbands'] = ta.bbands(df['close'])

# Custom logic
df['price_above_ma20'] = df['close'] > df['sma_20']
df['rsi_overbought'] = df['rsi_14'] > 70
df['rsi_oversold'] = df['rsi_14'] < 30
```

### 7.3 Prompt Format Pattern

```python
# Keep it simple: just the DataFrame as text
prompt = f"""
TOKEN: {symbol}
TIMEFRAME: 15m candles

Market Data:
{df.tail(20).to_string()}

Decide: Buy, Sell, or Do Nothing?
Response must be exactly one of these three words."""

# Or more detailed:
prompt = f"""
TOKEN: {symbol}
TIMEFRAME: 15m (15-minute candles)
TOTAL CANDLES: {len(df)}
DATE RANGE: {df.index[0]} to {df.index[-1]}

Price Action (Last 15 candles):
{df.tail(15).to_string()}

Full Dataset:
{df.to_string()}

Analyze and respond with ONLY: Buy, Sell, or Do Nothing"""
```

### 7.4 Multi-Model Consensus Pattern

```python
# Define voting models
models = [
    ('claude', 'claude-sonnet-4-5'),
    ('openai', 'gpt-4-turbo'),
    ('deepseek', 'deepseek-chat'),
]

# Parallel query
votes = {}
for model_type, model_name in models:
    model = model_factory.get_model(model_type, model_name)
    response = model.generate_response(system_prompt=TRADING_PROMPT, user_content=formatted_data)
    votes[model_name] = response.strip().upper()

# Calculate consensus
vote_counts = {}
for vote in votes.values():
    if "BUY" in vote:
        vote_counts['BUY'] = vote_counts.get('BUY', 0) + 1
    elif "SELL" in vote:
        vote_counts['SELL'] = vote_counts.get('SELL', 0) + 1
    else:
        vote_counts['DO NOTHING'] = vote_counts.get('DO NOTHING', 0) + 1

majority_action = max(vote_counts, key=vote_counts.get)
confidence = (vote_counts[majority_action] / len(models)) * 100
```

---

## 8. WHAT MOON DEV SKIPS (Simplifications)

✂️ **Not doing**:
- ❌ Sentiment analysis (only technical + orderbook)
- ❌ On-chain metrics (whale transactions, holder distribution)
- ❌ Social sentiment (no Twitter/Discord/TG monitoring)
- ❌ Cross-exchange arbitrage tracking
- ❌ Complex order management (no partial fills, averaging down/up)
- ❌ Portfolio optimization (simple MAX_POSITION_PERCENTAGE % instead)
- ❌ Risk analysis per position (just global stop-loss/take-profit)
- ❌ Funding rate tracking (for Aster/HyperLiquid shorts)
- ❌ Liquidation monitoring

---

## 9. WHAT MOON DEV SHOULD ADD (for Production)

✨ **Recommendations**:
- ✅ Retry logic with exponential backoff for API failures
- ✅ Rate limiting awareness (Birdeye free tier = ~10 req/sec)
- ✅ Stale data detection (timestamp too old → skip analysis)
- ✅ Model latency tracking (log response times per model)
- ✅ Consensus timeout handling (what if 1 model hangs?)
- ✅ Trade logging to database (not just memory)
- ✅ Webhook alerts on major trades (Slack, Discord, email)
- ✅ Graceful shutdown procedures
- ✅ Health checks (periodically verify API connectivity)

---

## 10. PERFORMANCE BENCHMARKS

**From Moon Dev's Testing**:

| Operation | Time | Notes |
|-----------|------|-------|
| Fetch Birdeye (1 token) | 50-150ms | API response + parsing |
| Fetch HyperLiquid (1 symbol) | 100-200ms | Includes retry logic |
| Calculate indicators (100 bars) | 10-50ms | pandas_ta overhead |
| Single model response | 2-8s | Depends on model |
| Swarm query (3-6 models) | 15-60s | Parallel execution |
| Full cycle (1 token) | 20-90s | Collection → analysis → decision |

**Timeframe Recommendation**:
- Minimum: 60s sleep between cycles (account for slowest model)
- Recommended: 300s (5 min) for 3-6 tokens
- Safe: 900s (15 min) for 10+ tokens

---

## 11. CRITICAL GOTCHAS & FIXES

### Gotcha #1: Timestamp Formats
**Problem**: APIs return timestamps in different formats (Unix seconds, milliseconds, strings)
**Fix**: Always parse to datetime, then convert to Unix ms for consistency
```python
# Birdeye returns Unix seconds
timestamp_sec = item['unixTime']
dt = datetime.utcfromtimestamp(timestamp_sec)

# HyperLiquid returns milliseconds
timestamp_ms = snapshot['t']
dt = datetime.utcfromtimestamp(timestamp_ms / 1000)
```

### Gotcha #2: Numeric String Conversions
**Problem**: Some APIs return prices as strings (e.g., "45000.5" instead of 45000.5)
**Fix**: Always convert to float64 explicitly
```python
df['close'] = df['close'].astype('float64')
```

### Gotcha #3: Missing Data Padding
**Problem**: New tokens have <40 candles, indicators fail
**Fix**: Replicate first row to reach minimum
```python
if len(df) < 40:
    first_row = pd.concat([df.iloc[0:1]] * (40 - len(df)))
    df = pd.concat([first_row, df])
```

### Gotcha #4: Indicator Length Validation
**Problem**: Can't calculate SMA(20) with only 10 candles
**Fix**: Always ensure sufficient data before indicator calculation
```python
if len(df) < 50:  # SMA(50) needs 50+ bars
    print("Warning: Not enough data for all indicators")
    # Either pad data or use fewer bars
```

### Gotcha #5: Cache Staleness
**Problem**: Old cached data used instead of fresh data
**Fix**: Always delete temp cache or validate timestamps
```python
# Delete cache every run
import shutil
shutil.rmtree('temp_data', ignore_errors=True)

# OR validate age
cache_file = f"temp_data/{token}.csv"
if os.path.exists(cache_file):
    age_minutes = (time.time() - os.path.getmtime(cache_file)) / 60
    if age_minutes > 15:  # Older than 15 min = stale
        os.remove(cache_file)
```

---

## 12. INTEGRATION CHECKLIST FOR PACIFICA

```
Data Pipeline:
[ ] Fetch OHLCV from Pacifica /kline endpoint
[ ] Support 15m, 1H, 4H timeframes
[ ] Cache data to temp_data/{symbol}.csv
[ ] Implement retry logic (3x, 10s timeout)
[ ] Handle missing/corrupted data gracefully

Processing:
[ ] Convert JSON → pandas DataFrame
[ ] Calculate SMA(20), RSI(14), MACD, BBands with pandas_ta
[ ] Validate all numeric types are float64
[ ] Detect and handle NaN values

Prompt Construction:
[ ] Format DataFrame as readable text
[ ] Include last 20 candles + summary stats
[ ] Add funding rates if available
[ ] Keep under 10,000 tokens for LLM efficiency

LLM Integration:
[ ] Query Claude Sonnet (preferred) or GPT-4
[ ] Expect exactly "Buy", "Sell", or "Do Nothing"
[ ] Log full response for debugging
[ ] Add confidence scoring

Execution:
[ ] Route Buy → n.market_buy() with slippage
[ ] Route Sell → n.market_sell() with slippage
[ ] Route Hold → skip order, continue monitoring
[ ] Add P&L monitoring (stop-loss, take-profit)

Testing:
[ ] Backtest on historical data
[ ] Paper trade for 1 week minimum
[ ] Monitor for API rate limits
[ ] Log all decisions to database
```

---

## 13. EXAMPLE: MINIMAL WORKING IMPLEMENTATION

```python
import requests
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta

# 1. FETCH DATA
def fetch_pacifica_data(symbol, days_back=3):
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)
    
    url = "https://api.pacifica.fi/api/v1/kline"
    params = {
        "symbol": symbol,
        "interval": "15m",
        "start_time": start_time,
        "limit": 288  # 3 days of 15m candles
    }
    
    response = requests.get(url, params=params)
    return response.json()['data']  # Assuming this is the response structure

# 2. PROCESS DATA
def process_to_dataframe(raw_data):
    df = pd.DataFrame(raw_data)
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    
    # Add indicators
    df['sma_20'] = ta.sma(df['close'], length=20)
    df['rsi'] = ta.rsi(df['close'], length=14)
    
    return df

# 3. FORMAT FOR LLM
def format_for_llm(symbol, df):
    return f"""
TOKEN: {symbol}
TIMEFRAME: 15m

Latest 20 candles:
{df.tail(20).to_string()}

Decide: Buy, Sell, or Do Nothing?
Response: """

# 4. QUERY LLM
def get_trading_decision(symbol):
    data = fetch_pacifica_data(symbol)
    df = process_to_dataframe(data)
    prompt = format_for_llm(symbol, df)
    
    # Use Claude (or your preferred model)
    from anthropic import Anthropic
    client = Anthropic()
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=10,
        messages=[{"role": "user", "content": prompt}]
    )
    
    decision = response.content[0].text.strip().upper()
    return decision, df

# 5. EXECUTE
symbol = "SOL"
decision, df = get_trading_decision(symbol)
print(f"Decision: {decision}")
print(f"Current price: ${df['close'].iloc[-1]:.4f}")
```

---

## Summary

Moon Dev's data pipeline is straightforward and pragmatic:
1. **Fetch OHLCV** from appropriate exchange API
2. **Process to DataFrame** with technical indicators
3. **Format as readable text** for LLM consumption
4. **Query multiple LLMs in parallel** for consensus votes
5. **Execute winning action** (Buy/Sell/Hold)

The key insights:
- **Simplicity wins**: 3-word responses are faster than nuanced analysis
- **Parallel voting**: 6 diverse models > 1 smart model
- **Timestamp handling**: Critical for multi-exchange systems
- **Data caching**: Speeds up repeated queries
- **Indicator selection**: SMA, RSI, MACD, BBands sufficient for most strategies

For Pacifica integration, the pattern is identical - just swap the API endpoint and adjust for Pacifica's specific response format.

