# Pacifica Trading Agent - Data Pipeline Implementation Plan

## Quick Reference

### Moon Dev Data Flow
```
Fetch OHLCV → Process to DataFrame → Add Indicators → Format Text → Query LLM Swarm → Execute
```

### For Pacifica
```
Pacifica /kline → DataFrame (pandas) → pandas_ta indicators → Readable text → Claude/GPT consensus → Trade execution
```

---

## Phase 1: Core Data Collection (Priority: IMMEDIATE)

### 1.1 Create Pacifica Data Collector

**File**: `src/data/pacifica_collector.py`

```python
import requests
import pandas as pd
from datetime import datetime, timedelta
import time

PACIFICA_BASE_URL = "https://api.pacifica.fi/api/v1"
PACIFICA_ACCOUNT = "8saejVsbEBraGvxbJGxrosv4QKMfR2i8f59GFAnMXfMc"

def fetch_pacifica_kline(symbol, interval="15m", days_back=3):
    """
    Fetch OHLCV from Pacifica /kline endpoint
    
    Args:
        symbol: Token symbol (SOL, BTC, ETH)
        interval: Timeframe (1m, 3m, 5m, 15m, 30m, 1H, 4H, 8H, 12H, 1D)
        days_back: Historical data window
    
    Returns:
        pandas DataFrame with columns: timestamp, open, high, low, close, volume
    """
    
    # Calculate time window
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)
    
    # Calculate bars needed
    bars_per_day = {
        '1m': 1440, '3m': 480, '5m': 288, '15m': 96, '30m': 48,
        '1h': 24, '2h': 12, '4h': 6, '6h': 4, '8h': 3, '12h': 2,
        '1d': 1
    }
    bars_needed = int(days_back * bars_per_day.get(interval, 96))
    
    # Make request with retry
    url = f"{PACIFICA_BASE_URL}/kline"
    params = {
        "symbol": symbol,
        "interval": interval,
        "start_time": start_time,
        "limit": bars_needed
    }
    
    for attempt in range(3):
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return _process_pacifica_response(data, symbol, interval)
            else:
                print(f"Status {response.status_code}: {response.text}")
                time.sleep(1)
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                time.sleep(2)
    
    return pd.DataFrame()

def _process_pacifica_response(raw_data, symbol, interval):
    """Convert Pacifica response to standard DataFrame"""
    
    if not raw_data:
        return pd.DataFrame()
    
    # Expected structure - adjust based on actual Pacifica response format
    processed = []
    for item in raw_data:
        processed.append({
            'timestamp': datetime.utcfromtimestamp(item.get('time', 0) / 1000),
            'open': float(item.get('o', 0)),
            'high': float(item.get('h', 0)),
            'low': float(item.get('l', 0)),
            'close': float(item.get('c', 0)),
            'volume': float(item.get('v', 0))
        })
    
    df = pd.DataFrame(processed)
    
    if len(df) < 40:  # Pad if insufficient data
        first_row = df.iloc[0:1].copy()
        padding = pd.concat([first_row] * (40 - len(df)), ignore_index=True)
        df = pd.concat([padding, df], ignore_index=True)
    
    return df

def get_funding_rates(symbol):
    """
    Fetch funding rates from Pacifica /info endpoint
    
    Note: Used to add funding rate context to trading decisions
    Useful for shorts on Aster/HyperLiquid
    """
    url = f"{PACIFICA_BASE_URL}/info"
    params = {"symbol": symbol}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                'funding_rate': data.get('fundingRate', 0),
                'mark_price': data.get('markPrice', 0),
                'open_interest': data.get('openInterest', 0)
            }
    except Exception as e:
        print(f"Error fetching funding rates: {e}")
    
    return None
```

### 1.2 Add to ohlcv_collector.py

Modify `/src/data/ohlcv_collector.py` to support Pacifica:

```python
def collect_token_data(token, days_back=DAYSBACK_4_DATA, timeframe=DATA_TIMEFRAME, exchange="PACIFICA"):
    """Extend to support PACIFICA exchange"""
    
    if exchange == "PACIFICA":
        from src.data.pacifica_collector import fetch_pacifica_kline
        data = fetch_pacifica_kline(token, timeframe, days_back)
    elif exchange == "HYPERLIQUID":
        data = hl.get_data(symbol=token, timeframe=hl_timeframe, bars=bars_needed)
    # ... rest of dispatching logic
    
    return data
```

---

## Phase 2: Technical Indicator Processing (Priority: HIGH)

### 2.1 Create Indicator Module

**File**: `src/indicators/pacifica_indicators.py`

```python
import pandas as pd
import pandas_ta as ta

def add_pacifica_indicators(df):
    """Add all technical indicators for Pacifica trading"""
    
    if df.empty or len(df) < 50:
        return df
    
    try:
        # Ensure numeric types
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        df[numeric_cols] = df[numeric_cols].astype('float64')
        
        # Core indicators
        df['sma_20'] = ta.sma(df['close'], length=20)
        df['sma_50'] = ta.sma(df['close'], length=50)
        df['rsi_14'] = ta.rsi(df['close'], length=14)
        
        # MACD
        macd_result = ta.macd(df['close'])
        df = pd.concat([df, macd_result], axis=1)
        
        # Bollinger Bands
        bbands_result = ta.bbands(df['close'])
        df = pd.concat([df, bbands_result], axis=1)
        
        # ATR (volatility)
        df['atr_14'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        # Additional useful signals
        df['price_above_sma20'] = df['close'] > df['sma_20']
        df['price_above_sma50'] = df['close'] > df['sma_50']
        df['rsi_oversold'] = df['rsi_14'] < 30
        df['rsi_overbought'] = df['rsi_14'] > 70
        
        print(f"✅ Added {len(df.columns)} columns with technical indicators")
        return df
        
    except Exception as e:
        print(f"❌ Error adding indicators: {e}")
        return df

def get_signal_summary(df):
    """Get summary of current signals for prompt context"""
    
    if df.empty:
        return None
    
    latest = df.iloc[-1]
    
    return {
        'price': float(latest['close']),
        'sma_20': float(latest['sma_20']) if 'sma_20' in df else None,
        'sma_50': float(latest['sma_50']) if 'sma_50' in df else None,
        'rsi': float(latest['rsi_14']) if 'rsi_14' in df else None,
        'above_sma20': bool(latest['price_above_sma20']) if 'price_above_sma20' in df else None,
        'above_sma50': bool(latest['price_above_sma50']) if 'price_above_sma50' in df else None,
        'overbought': bool(latest['rsi_overbought']) if 'rsi_overbought' in df else None,
        'oversold': bool(latest['rsi_oversold']) if 'rsi_oversold' in df else None
    }
```

---

## Phase 3: LLM Prompt Construction (Priority: HIGH)

### 3.1 Create Prompt Formatter

**File**: `src/agents/pacifica_prompt_formatter.py`

```python
import json

PACIFICA_TRADING_PROMPT = """You are an expert cryptocurrency trading AI analyzing market data from Pacifica DEX.

CRITICAL RULES:
1. Your response MUST be EXACTLY one of these three words: Buy, Sell, or Do Nothing
2. Do NOT provide any explanation, reasoning, or additional text
3. Respond with ONLY the action word

Market Data Analysis:
- "Buy" = Strong bullish technical signals, recommend opening/holding position
- "Sell" = Bearish signals or weakness, recommend closing position
- "Do Nothing" = Unclear signals, recommend holding current state

RESPOND WITH ONLY ONE WORD: Buy, Sell, or Do Nothing"""

def format_pacifica_market_data(symbol, df, funding_rates=None):
    """
    Format market data for LLM analysis
    
    Args:
        symbol: Trading symbol (SOL, BTC, etc)
        df: DataFrame with OHLCV + indicators
        funding_rates: Optional dict with funding rate context
    
    Returns:
        Formatted string for LLM input
    """
    
    if df.empty:
        return None
    
    # Key stats
    current_price = df['close'].iloc[-1]
    price_change = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
    
    # Build formatted string
    formatted = f"""
TOKEN: {symbol}
TIMEFRAME: 15-minute candles
TOTAL CANDLES: {len(df)}
DATE RANGE: {df['timestamp'].min()} to {df['timestamp'].max()}

CURRENT PRICE: ${current_price:.8f}
24H CHANGE: {price_change:+.2f}%

RECENT PRICE ACTION (Last 10 candles):
{df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].tail(10).to_string(index=False)}

TECHNICAL INDICATORS (Last 5 candles):
{df[['timestamp', 'sma_20', 'sma_50', 'rsi_14']].tail(5).to_string(index=False)}

FULL DATASET:
{df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].to_string(index=False)}
"""
    
    # Add funding rate context if available
    if funding_rates:
        formatted += f"""
FUNDING RATE CONTEXT:
- Current Funding Rate: {funding_rates.get('funding_rate', 'N/A')}%
- Mark Price: ${funding_rates.get('mark_price', 'N/A')}
- Open Interest: ${funding_rates.get('open_interest', 'N/A')}
"""
    
    return formatted

def parse_llm_decision(response_text):
    """
    Parse LLM response to trading decision
    
    Returns:
        str: "BUY", "SELL", or "NOTHING" (normalized)
    """
    
    text = response_text.strip().upper()
    
    if "BUY" in text:
        return "BUY"
    elif "SELL" in text:
        return "SELL"
    else:
        return "NOTHING"
```

---

## Phase 4: LLM Integration (Priority: HIGH)

### 4.1 Single Model Wrapper

**File**: `src/agents/pacifica_trading_agent.py`

```python
from anthropic import Anthropic
from src.agents.pacifica_prompt_formatter import (
    PACIFICA_TRADING_PROMPT,
    format_pacifica_market_data,
    parse_llm_decision
)

class PacificaTradingAgent:
    def __init__(self, model="claude-3-5-sonnet-20241022"):
        self.client = Anthropic()
        self.model = model
    
    def get_trading_decision(self, symbol, df, funding_rates=None):
        """
        Query LLM for trading decision
        
        Returns:
            tuple: (decision, confidence, reasoning)
        """
        
        # Format market data
        formatted_data = format_pacifica_market_data(symbol, df, funding_rates)
        if not formatted_data:
            return "NOTHING", 0, "No data available"
        
        # Query LLM
        response = self.client.messages.create(
            model=self.model,
            max_tokens=10,  # Only need one word
            system=PACIFICA_TRADING_PROMPT,
            messages=[
                {"role": "user", "content": formatted_data}
            ]
        )
        
        # Parse response
        response_text = response.content[0].text
        decision = parse_llm_decision(response_text)
        
        return decision, 100, response_text  # 100% confidence for single model

def analyze_pacifica_token(symbol, days_back=3):
    """
    End-to-end analysis for a Pacifica token
    
    1. Fetch OHLCV data
    2. Add technical indicators
    3. Query LLM
    4. Return decision
    """
    from src.data.pacifica_collector import fetch_pacifica_kline
    from src.indicators.pacifica_indicators import add_pacifica_indicators
    
    # Collect data
    df = fetch_pacifica_kline(symbol, "15m", days_back)
    if df.empty:
        return None
    
    # Add indicators
    df = add_pacifica_indicators(df)
    
    # Get LLM decision
    agent = PacificaTradingAgent()
    decision, confidence, reasoning = agent.get_trading_decision(symbol, df)
    
    return {
        'symbol': symbol,
        'decision': decision,
        'confidence': confidence,
        'reasoning': reasoning,
        'current_price': df['close'].iloc[-1],
        'data_points': len(df)
    }
```

---

## Phase 5: Multi-Model Consensus (Optional, Priority: MEDIUM)

For voting with multiple models (Claude, GPT-4, DeepSeek):

```python
from concurrent.futures import ThreadPoolExecutor
import anthropic
import openai

def get_swarm_consensus(symbol, df, funding_rates=None):
    """
    Get trading decision from multiple AI models via voting
    
    Models:
    - Claude Sonnet 3.5 (balanced)
    - GPT-4 Turbo (visual patterns)
    - DeepSeek Chat (contrarian)
    """
    
    models = [
        ('claude', Anthropic(), 'claude-3-5-sonnet-20241022'),
        ('openai', openai.OpenAI(), 'gpt-4-turbo'),
        # ('deepseek', deepseek_client, 'deepseek-chat'),
    ]
    
    formatted_data = format_pacifica_market_data(symbol, df, funding_rates)
    votes = {}
    
    # Query each model in parallel
    with ThreadPoolExecutor(max_workers=len(models)) as executor:
        futures = {}
        
        for model_name, client, model_id in models:
            future = executor.submit(
                _query_model,
                model_name, client, model_id,
                formatted_data
            )
            futures[future] = model_name
        
        # Collect results
        for future in futures:
            model_name = futures[future]
            try:
                decision = future.result(timeout=30)
                votes[model_name] = decision
            except Exception as e:
                print(f"Error from {model_name}: {e}")
    
    # Calculate consensus
    decision_counts = {}
    for decision in votes.values():
        decision_counts[decision] = decision_counts.get(decision, 0) + 1
    
    majority_decision = max(decision_counts, key=decision_counts.get)
    confidence = int((decision_counts[majority_decision] / len(votes)) * 100)
    
    return majority_decision, confidence, votes

def _query_model(model_name, client, model_id, prompt_text):
    """Query a single model"""
    try:
        response = client.messages.create(
            model=model_id,
            max_tokens=10,
            system=PACIFICA_TRADING_PROMPT,
            messages=[{"role": "user", "content": prompt_text}]
        )
        text = response.content[0].text
        return parse_llm_decision(text)
    except Exception as e:
        raise e
```

---

## Phase 6: Trade Execution Integration (Priority: MEDIUM)

### 6.1 Connect to Existing Execution

**File**: `src/agents/pacifica_trading_agent.py` (extended)

```python
def execute_pacifica_trade(symbol, decision, current_price, slippage=199):
    """
    Execute trade based on LLM decision
    
    Routes to existing Pacifica trading functions
    """
    from src import nice_funcs_extended as n
    
    if decision == "BUY":
        # Get current balance
        balance = n.get_account_balance()  # Assuming this exists
        position_size = balance * 0.25  # Risk 25% per trade
        
        print(f"Opening BUY position: ${position_size:.2f}")
        return n.market_buy(symbol, position_size, slippage)
    
    elif decision == "SELL":
        # Close any existing position
        current_position = n.get_token_balance_usd(symbol)
        if current_position > 0:
            print(f"Closing position: ${current_position:.2f}")
            return n.market_sell(symbol, current_position, slippage)
    
    elif decision == "NOTHING":
        # Hold current position, take no action
        return None
```

---

## Phase 7: Testing & Validation (Priority: HIGH)

### 7.1 Backtesting Framework

```python
# test_pacifica_pipeline.py

import pandas as pd
from datetime import datetime, timedelta
from src.data.pacifica_collector import fetch_pacifica_kline
from src.indicators.pacifica_indicators import add_pacifica_indicators
from src.agents.pacifica_trading_agent import PacificaTradingAgent

def backtest_single_token(symbol, start_date, end_date):
    """
    Backtest trading strategy on historical data
    
    Returns:
        DataFrame with decisions and performance
    """
    
    # Fetch historical data
    df = fetch_pacifica_kline(symbol, "15m", days_back=30)
    
    # Add indicators
    df = add_pacifica_indicators(df)
    
    # Simulate trading
    agent = PacificaTradingAgent()
    decisions = []
    
    for i in range(50, len(df)):  # Start after indicators stabilize
        window = df.iloc[:i]
        decision, _, _ = agent.get_trading_decision(symbol, window)
        decisions.append({
            'timestamp': df.iloc[i]['timestamp'],
            'price': df.iloc[i]['close'],
            'decision': decision,
            'next_price': df.iloc[i+1]['close'] if i+1 < len(df) else None
        })
    
    return pd.DataFrame(decisions)

def test_prompt_formatting():
    """Unit test: Verify prompt formatting"""
    
    df = pd.DataFrame({
        'timestamp': pd.date_range('2025-01-01', periods=100, freq='15min'),
        'open': [100.0] * 100,
        'high': [101.0] * 100,
        'low': [99.0] * 100,
        'close': [100.5] * 100,
        'volume': [1000.0] * 100,
        'sma_20': [100.0] * 100,
        'sma_50': [100.0] * 100,
        'rsi_14': [50.0] * 100
    })
    
    from src.agents.pacifica_prompt_formatter import format_pacifica_market_data
    
    prompt = format_pacifica_market_data("SOL", df)
    assert "SOL" in prompt
    assert "OHLCV" in prompt or "close" in prompt
    print("✅ Prompt formatting test passed")

def test_api_connectivity():
    """Test: Verify Pacifica API is reachable"""
    
    try:
        df = fetch_pacifica_kline("SOL", "15m", days_back=1)
        assert not df.empty
        print(f"✅ Pacifica API test passed ({len(df)} candles)")
    except Exception as e:
        print(f"❌ Pacifica API test failed: {e}")
```

---

## Phase 8: Configuration & Deployment (Priority: MEDIUM)

### 8.1 Add to config.py

```python
# Pacifica-specific settings
EXCHANGE = "PACIFICA"  # NEW: Add Pacifica as exchange option
PACIFICA_SYMBOLS = ["SOL", "BTC", "ETH"]  # NEW: Symbols to trade on Pacifica
PACIFICA_LEVERAGE = 1  # NEW: Pacifica leverage (if supported)

# Data collection
DATA_TIMEFRAME = "15m"  # Already supports Pacifica intervals
DAYSBACK_4_DATA = 3

# AI Model
USE_SWARM_MODE = False  # Start with single model for speed
AI_MODEL_TYPE = "claude"
AI_MODEL_NAME = "claude-3-5-sonnet-20241022"
```

### 8.2 Environment Variables

Add to `.env`:
```
PACIFICA_API_KEY=<if required>
PACIFICA_ACCOUNT=8saejVsbEBraGvxbJGxrosv4QKMfR2i8f59GFAnMXfMc
```

---

## Implementation Checklist

### Phase 1: Data Collection
- [ ] Create `src/data/pacifica_collector.py`
- [ ] Implement `fetch_pacifica_kline()`
- [ ] Test with live Pacifica API
- [ ] Verify response format matches docs
- [ ] Implement caching to `temp_data/`
- [ ] Handle errors gracefully

### Phase 2: Indicators
- [ ] Create `src/indicators/pacifica_indicators.py`
- [ ] Implement all required indicators (SMA, RSI, MACD, BBands)
- [ ] Test with sample data
- [ ] Verify indicator calculations match external sources

### Phase 3: LLM Prompts
- [ ] Create `src/agents/pacifica_prompt_formatter.py`
- [ ] Design clean prompt format
- [ ] Test parsing of LLM responses
- [ ] Validate 3-word decision format

### Phase 4: LLM Integration
- [ ] Create `src/agents/pacifica_trading_agent.py`
- [ ] Connect to Claude API
- [ ] Test end-to-end (fetch → indicators → prompt → decision)
- [ ] Log all decisions to file

### Phase 5: Consensus (Optional)
- [ ] Implement swarm voting
- [ ] Add multi-model parallel execution
- [ ] Calculate consensus confidence

### Phase 6: Trade Execution
- [ ] Connect to Pacifica trading functions
- [ ] Implement Buy/Sell/Hold routing
- [ ] Add position sizing logic
- [ ] Add stop-loss/take-profit

### Phase 7: Testing
- [ ] Unit tests for each module
- [ ] Integration tests (full pipeline)
- [ ] Backtest on historical data
- [ ] Paper trade for 1 week

### Phase 8: Deployment
- [ ] Update config.py
- [ ] Set environment variables
- [ ] Deploy to production
- [ ] Monitor for issues

---

## Estimated Timeline

| Phase | Task | Days | Status |
|-------|------|------|--------|
| 1 | Data Collection | 1-2 | Next |
| 2 | Indicators | 1 | Next |
| 3 | Prompt Formatting | 1 | Next |
| 4 | LLM Integration | 1 | Next |
| 5 | Multi-Model (Optional) | 1 | Next |
| 6 | Trade Execution | 1-2 | Next |
| 7 | Testing | 2-3 | Next |
| 8 | Deployment | 1 | Next |
| | **TOTAL** | **9-13 days** | In Progress |

---

## Key Success Metrics

Track these during implementation:

1. **Data Freshness**: Pacifica candles < 5 minutes old
2. **Indicator Accuracy**: Compare to external sources ±0.1%
3. **LLM Response Time**: < 5 seconds per decision
4. **Decision Consistency**: Same input = same output
5. **API Reliability**: 99%+ uptime on /kline endpoint
6. **Backtest Results**: Track Win Rate, Profit Factor, Sharpe Ratio

---

## Next Steps

1. **Immediate**: Implement Phase 1 (Data Collection)
   - Test Pacifica /kline endpoint
   - Verify response format
   - Implement caching

2. **This Week**: Implement Phases 2-4 (Indicators + LLM)
   - Add technical indicators
   - Create prompt formatter
   - Connect to Claude API

3. **Next Week**: Testing & Deployment
   - Backtest strategy
   - Paper trade
   - Deploy to production

---

## Questions to Clarify

- [ ] What is the exact response format of Pacifica /kline?
- [ ] What funding rates are available via /info?
- [ ] What's the maximum request rate for /kline endpoint?
- [ ] Does Pacifica support all timeframes (1m, 5m, 15m, 1H, etc)?
- [ ] Should we implement funding rate logic for shorts?
- [ ] What's the minimum order size on Pacifica?
- [ ] Are there any rate limits we should respect?

