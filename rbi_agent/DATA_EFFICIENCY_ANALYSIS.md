# CSV vs API Efficiency Analysis

## Moon Dev's Approach

**Current Moon Dev Workflow**:
```
1. Fetch data from API (Birdeye/CoinGecko) → Save CSV
2. Generate backtest code that reads CSV
3. Run backtest (subprocess) → reads CSV file
4. Repeat for optimization (10 iterations) → reads same CSV
```

**Why CSV is Efficient for Moon Dev**:
- ✅ **Fetched once, used many times**: Each optimization iteration reads the same CSV
- ✅ **No API rate limits**: CSV reads are instant (no API calls)
- ✅ **Parallel processing**: 18 threads can all read the same CSV simultaneously
- ✅ **Separate processes**: Each backtest runs as subprocess → needs file access
- ✅ **Works offline**: Once CSV exists, no internet needed

**If we used API directly**:
- ❌ **API call every iteration**: 10 optimization iterations = 10 API calls
- ❌ **Rate limits**: Cambrian API might throttle
- ❌ **Slower**: Network latency vs file read
- ❌ **Parallel issues**: Multiple threads hitting API simultaneously

---

## Best Approach: **Hybrid (Fetch API → Cache CSV)**

### Option 1: CSV Cache (Recommended)
```python
# Fetch from Cambrian API → Save CSV → Moon Dev reads CSV
1. Fetch from Cambrian (90 days, 1 API call)
2. Save to CSV (moon-dev-reference/src/data/rbi/SOL-USD-15m.csv)
3. Moon Dev RBI agent reads CSV (fast, cached)
4. Optimization runs 10x → reads same CSV (no API calls)
```

**Efficiency**: 
- ✅ 1 API call vs 10+ API calls
- ✅ Fast CSV reads (instant)
- ✅ Works with Moon Dev's existing code
- ✅ No code changes needed

### Option 2: Modify Moon Dev's Code (More Complex)
```python
# Add Cambrian to ohlcv_collector.py
# Modify backtest prompt to use API directly
# Requires changing Moon Dev's system prompts
```

**Efficiency**:
- ⚠️ More complex (modify their prompts)
- ⚠️ API calls on every backtest run
- ⚠️ Slower (network latency)
- ⚠️ Risk of rate limits

---

## Recommendation: **Use CSV Cache**

**Why CSV is MORE efficient**:
1. **One fetch, many uses**: Fetch 90 days once → use for 10 optimization iterations
2. **Instant reads**: CSV read is ~10ms vs API call ~500ms+
3. **No rate limits**: File system has no limits
4. **Moon Dev expects CSV**: Their code already uses CSV
5. **Parallel safe**: Multiple threads reading CSV = no conflicts

**Implementation**:
```python
# Our adapter: Cambrian API → CSV
cambrian_fetcher.fetch_ohlcv() → Save CSV → Moon Dev reads CSV
```

**Result**: 
- ✅ Fast (cached)
- ✅ Efficient (1 API call vs 10+)
- ✅ Works with Moon Dev's code
- ✅ Always fresh (can refresh CSV when needed)

---

**Conclusion**: CSV cache is MORE efficient than API calls for Moon Dev's workflow!

