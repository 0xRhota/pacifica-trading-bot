# Deep42 Social Intelligence - Test Results

## Agent Endpoint ✅ WORKING

**Base URL**: `https://deep42.cambrian.network/api/v1/deep42/agents/social-data`

**Authentication**: `X-API-Key: doug.ZbEScx8M4zlf7kDn`

## What Deep42 Provides

This is an **AI agent** that analyzes Twitter/social data for crypto tokens. You ask natural language questions, it runs analysis tools and returns structured insights.

### Key Capabilities:

1. **Alpha Tweet Detection**
   - Identifies high-value tweets from credible sources
   - Scores tweets on quality (30+ = exceptional, 25-30 = high quality, 20-25 = good)
   - Returns actual tweet content and author handles

2. **Token Social Leaderboard**
   - Ranks tokens by social activity
   - Shows tweet volume, unique users, average alpha score
   - Helps identify what's trending on crypto Twitter

3. **Influencer Tracking**
   - Identifies top crypto influencers discussing tokens
   - Shows their tweet volume and average alpha scores
   - Helps gauge credibility of social signals

4. **Sentiment Analysis**
   - Detects sentiment shifts (bullish/bearish changes)
   - Monitors social momentum
   - Identifies viral signals early

## Test Results for Your Tokens

**Query**: "What are the current social signals and alpha tweets for SOL, PENGU, HYPE, and XPL tokens?"

**Result**: No alpha tweets found for these specific tokens in last 24-48h

This means:
- Either these tokens are quiet on Twitter right now
- Or they don't have high-scoring alpha content recently
- Need broader queries to see overall social landscape

## Example: SOL Social Landscape

From the docs example, when asked "What are the current social signals and trends for SOL token?":

**SOL ranked 8th** in social leaderboard:
- **74 tweets** in 24-48h
- **14.2 avg alpha score** (good insights quality)
- **18 peak score** (highest single tweet)
- **55 unique users** discussing

**Top tokens by social activity**:
1. BTC - 140 tweets, 14.0 avg score
2. VIRTUAL - 131 tweets, 13.76 avg score
3. TEN - 126 tweets, 14.13 avg score
...
8. SOL - 74 tweets, 14.2 avg score

## How This Could Help Perp Trading

### Option 1: Social Sentiment Filter
Before opening a long:
```python
# Ask: "Is there strong bullish sentiment for SOL right now?"
# If response shows high alpha scores + rising momentum → proceed
# If response shows bearish signals or low activity → skip
```

### Option 2: Alpha Signal Alerts
```python
# Ask: "Show me exceptional alpha tweets (score 30+) for SOL"
# If high-quality alpha appears → investigate as potential entry
# Use as early warning system for momentum plays
```

### Option 3: Comparative Analysis
```python
# Ask: "Compare social sentiment for SOL vs HYPE vs PENGU"
# Trade the token with strongest social signals
# Avoid tokens with deteriorating sentiment
```

### Option 4: Influencer Tracking
```python
# Ask: "Which major influencers are bullish on SOL?"
# If credible influencers are posting → confirms trade thesis
# If influencers are silent/bearish → reconsider
```

## Key Metrics from Response

The agent returns structured data including:

| Metric | Description | Trading Use |
|--------|-------------|-------------|
| `topTokenTweetCount` | Volume of social discussion | Higher = more attention |
| `topTokenAvgScore` | Average quality of tweets | Higher = better insights |
| `exceptionalAlphaCount` | Count of score 30+ tweets | Signals major news/movement |
| `trendingSignalsCount` | Number of trending signals | Momentum indicator |
| `topInfluencerHandle` | Most active credible voice | Sentiment direction |
| `totalAlphaTweets` | Total high-quality tweets | Overall social strength |

## Limitations Discovered

1. **Query Specificity**: Asking for specific tokens (SOL, PENGU, HYPE, XPL) returned "no tweets found"
   - Might need broader queries like "trending Solana tokens"
   - Or individual token queries: "What's the sentiment for SOL?"

2. **Recency Window**: Data from "last 24-48 hours"
   - Good for real-time signals
   - But misses longer-term sentiment trends

3. **Token Coverage**: Unknown if all tokens (especially smaller ones like XPL, ASTER) have Twitter data

## What to Test Next

1. **Individual token queries**:
   - "What's the current sentiment and alpha signals for SOL?"
   - "Show me trending signals for PENGU"
   - "Are there any exceptional alpha tweets about HYPE?"

2. **Broader discovery queries**:
   - "What tokens are trending with high social momentum right now?"
   - "Show me the top 10 tokens by social activity"
   - "Which Solana tokens have exceptional alpha tweets?"

3. **Time-sensitive queries**:
   - "Has SOL sentiment shifted in the last 24 hours?"
   - "What tokens are seeing rapidly increasing social activity?"

## Integration Ideas (For Discussion)

### Conservative Approach:
- Check social sentiment before opening positions
- Skip trades when social signals are bearish
- Manual review of agent responses

### Aggressive Approach:
- Automated queries every 15 minutes
- Parse response for alpha scores and tweet counts
- Auto-adjust position sizing based on social strength

### Hybrid Approach:
- Use as **confirmation** signal (not primary)
- Combine with on-chain buy/sell ratio from Cambrian
- Require both social + on-chain alignment to trade

## Questions for You

1. **What would you actually use this for?**
   - Early warning of sentiment shifts?
   - Confirmation before entering trades?
   - Discovery of trending tokens to trade?
   - Something else?

2. **What threshold makes sense?**
   - Only trade tokens with 20+ alpha score tweets?
   - Require 50+ unique users discussing?
   - Need exceptional (30+) alpha signals?

3. **How real-time does this need to be?**
   - Check once before each trade (every 15 min)?
   - Monitor continuously in background?
   - Daily summary to guide next day's trades?

4. **Which tokens should we focus on?**
   - Just SOL (we know it has coverage)?
   - Your full list (SOL, BTC, ETH, PENGU, XPL, HYPE, ASTER)?
   - Discover new trending tokens?
