# Cambrian API Deep Research - Actual Findings

## What I Found (Let's Discuss)

I explored the Cambrian API and found **two main categories** of data:

### 1. **On-Chain Solana Trading Data** (What I tested)
- Trade statistics (buy/sell counts, volume, ratios)
- OHLCV price data (multiple timeframes)
- Token holder data
- Pool analytics (Meteora, Raydium, Orca)
- Trader leaderboards

**Example**: SOL currently has 0.19 buy/sell ratio (7.8M sells vs 2.6M buys) = heavy selling pressure

### 2. **Deep42 Social Intelligence** (Haven't tested yet)
This is the **off-chain data** you mentioned. It's all about social media/Twitter analysis:

#### Available Deep42 Endpoints:

**Token Social Analysis** (`/deep42/social-data/token-analysis`)
- Twitter sentiment scores (0-10 scale)
- Tweet volume and engagement metrics
- Unique author counts
- Time-series analysis (hourly, daily, etc.)
- Sentiment distribution (bullish/neutral/bearish %)

**Alpha Tweet Detection** (`/deep42/social-data/alpha-tweet-detection`)
- Scores tweets on 4 dimensions:
  - Sentiment (how bullish/bearish)
  - Alpha value (is this actionable info?)
  - Legitimacy (is this credible?)
  - Technical accuracy (is the analysis sound?)
- Filters for high-scoring "alpha" tweets
- Returns actual tweet URLs to verify

**Trending Momentum** (`/deep42/social-data/trending-momentum`)
- Tweet velocity (tweets per hour increasing)
- Engagement velocity (likes/RTs per hour)
- Quality scores
- Momentum tiers: Low/Medium/High/Explosive
- Trend direction: Rising/Stable/Declining

**Influencer Credibility** (`/deep42/social-data/influencer-credibility`)
- Track record of crypto influencers
- Accuracy metrics
- Influence scores

**Sentiment Shifts** (`/deep42/social-data/sentiment-shifts`)
- Detects major sentiment changes
- Could signal market movements

## Questions for You

### 1. **What did you mean by "perp risk engine"?**
I didn't find anything specifically called a "perp risk engine" in the docs. Were you thinking of:
- The Deep42 social data (Twitter sentiment, etc.)?
- Something else you've seen before?
- A different Cambrian product?

### 2. **How do YOU think we should use this data?**
I see a few options but want your input:

**Option A: Social Sentiment as Entry Filter**
- Don't open longs when Twitter sentiment is bearish
- Look for rising momentum scores before entering
- Confirm with alpha tweet detection

**Option B: Combine On-Chain + Social**
- On-chain: buy/sell ratio (what's actually happening)
- Social: sentiment (what people are saying)
- Trade only when BOTH align

**Option C: Alpha Signal Hunting**
- Monitor alpha tweet detection for your tokens (SOL, BTC, ETH, PENGU, XPL, HYPE, ASTER)
- When high-scoring alpha tweets appear, that's a signal to pay attention
- Use as early warning system

**Option D: Something else you're thinking of?**

### 3. **What tokens should we actually focus on?**
You mentioned: XPL, PENGU, SOL, BTC, ETH, HYPE, ASTER

Which ones are you ACTUALLY trading perps on? Because:
- I can test the social data for these specific tokens
- See what kind of signals we get
- Figure out what's useful vs noise

### 4. **What problem are you trying to solve?**
Is it:
- Better entry timing? (when to open positions)
- Better exit timing? (when to close)
- Position sizing? (how much to risk)
- Asset selection? (which tokens to trade)
- Risk management? (when NOT to trade)

## What I DON'T Know Yet

1. **Quality of Deep42 data**
   - Is the Twitter sentiment actually predictive?
   - Or is it lagging (sentiment follows price)?
   - Need to test with real data

2. **Signal timing**
   - How far ahead does social sentiment move vs price?
   - Or does price move first, THEN Twitter reacts?

3. **For your specific tokens**
   - Are XPL, PENGU, HYPE, ASTER even covered by Deep42?
   - Do they have enough Twitter volume to be useful?
   - Or is this only good for majors (SOL, BTC, ETH)?

4. **Integration approach**
   - Real-time monitoring (expensive, complex)?
   - Periodic checks (every 15min when considering new trade)?
   - Manual dashboard (you check it yourself)?

## My Actual Recommendation

Before building anything, let's:

1. **Test Deep42 with your tokens**
   - Run social analysis on SOL, PENGU, HYPE
   - See what the data actually looks like
   - Check if it's useful or just noise

2. **Compare to recent price action**
   - Look at last 7 days of sentiment vs price moves
   - Did high sentiment predict pumps?
   - Did negative sentiment predict dumps?

3. **Decide THEN implement**
   - Once we know what's useful
   - Build the right integration
   - Not just "use all the data"

## Questions Back to You

1. What did you mean by "perp risk engine"?
2. What specific problem are you trying to solve with Cambrian data?
3. Which tokens are you ACTUALLY trading?
4. Should I test the Deep42 social data to see what it shows?
5. What would make this data useful to you?

I jumped ahead before - let's ideate properly this time.
