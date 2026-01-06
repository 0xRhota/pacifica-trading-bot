# PRD: Trading Bot Profitability Improvements
**Date:** 2025-11-08
**Status:** 🚧 IN PROGRESS
**Owner:** Claude Code (Sonnet 4.5)
**Priority:** 🔴 CRITICAL - Bots bleeding money

---

## 📋 Executive Summary

**Problem:** Both Pacifica and Lighter trading bots are slowly bleeding money due to low win rates and high trading frequency. Pacifica bot has 6.1% win rate (15 wins / 246 losses) and burns ~$160/day in fees while only losing ~$2/day on raw trades.

**Goal:** Achieve break-even or profitability while maintaining sufficient trading volume for Pacifica points farming.

**Approach:**
1. Improve trade selection quality (Deep42 sentiment, higher confidence)
2. Research Microsoft Agent Lightning for advanced strategies
3. Explore additional indicators and data sources
4. Test improvements in parallel dry-runs before deploying

**Timeline:** 2-7 days (immediate fixes + long-term research)

---

## 🎯 Success Criteria

### Primary Goals (MUST ACHIEVE)
- [ ] **Win Rate:** Improve from 6.1% → >25%
- [ ] **Daily P&L:** Break-even or positive (currently -$2-5/day)
- [ ] **Fee Efficiency:** Reduce fee burn from $160/day → <$50/day
- [ ] **Volume Maintained:** Keep sufficient volume for points farming (define minimum)

### Secondary Goals (NICE TO HAVE)
- [ ] **Sharpe Ratio:** >0.5 (currently negative)
- [ ] **Max Drawdown:** <10% of account
- [ ] **Profit Target:** $50-100/month positive returns
- [ ] **Automation:** Fully autonomous operation without manual intervention

---

## 🔍 Current State Analysis

### Pacifica Bot Status
- **Account:** YOUR_ACCOUNT_PUBKEY
- **Equity:** $113.23 (down from $113.75)
- **Win Rate:** 6.1% (15 wins / 246 losses)
- **Trading Frequency:** Every 5 minutes (288 checks/day)
- **Position Size:** $375 per trade (331% of account with leverage)
- **Daily Volume:** ~$200k notional
- **Daily Fees:** ~$160 (0.08% round-trip * volume)
- **Raw P&L:** -$1.95 (barely negative)
- **Net Loss:** ~$58.20 (fees are the killer)

### Lighter Bot Status
- **Markets:** 101+ (BTC, SOL, ETH, PENGU, ZEC, etc.)
- **Fees:** ✅ ZERO (Lighter DEX has no trading fees)
- **Position Size:** $5-10 margin per trade
- **Status:** Also slowly bleeding (need similar analysis)

### Root Causes
1. **Low win rate** - DeepSeek LLM making poor decisions (6.1% success)
2. **High frequency** - 5-min intervals = excessive fee burn
3. **Weak trade selection** - 0.60-0.72 confidence trades executed
4. **Underutilized data** - Deep42 sentiment available but not used for filtering
5. **Market context mismatch** - Bot shorts SOL when Deep42 shows 88.5% bullish
6. **Insufficient indicators** - Only using RSI, MACD, EMAs - need more?

---

## 📊 Requirements

### REQ-1: Immediate Profitability Fixes

#### REQ-1.1: Deep42 Sentiment Filtering
**Priority:** 🔴 CRITICAL
**Effort:** 2-4 hours
**Impact:** Win rate 6% → 15-25% (estimated)

**Description:**
Integrate Deep42 social sentiment as a pre-trade filter. Bot currently uses Deep42 for macro context but doesn't filter individual trades based on token-specific sentiment.

**Acceptance Criteria:**
- [ ] Before opening BUY position: Require >60% bullish sentiment
- [ ] Before opening SELL position: Require >40% bearish sentiment
- [ ] Skip trades that don't meet sentiment threshold
- [ ] Log sentiment data with each decision
- [ ] Add `--sentiment-threshold` CLI argument for testing
- [ ] Test in dry-run for 24-48 hours before deploying

**Technical Details:**
- File: `pacifica_agent/execution/pacifica_executor.py:133-199`
- Add `_check_sentiment_alignment()` method
- Call Deep42 `/api/perpdex/deep42/token-analysis` endpoint
- Cache sentiment for 5-15 minutes to reduce API calls

**Related Issues:**
- Bot shorting SOL with 88.5% bullish sentiment
- 246 losing trades out of 261 total

---

#### REQ-1.2: Minimum Confidence Threshold
**Priority:** 🔴 HIGH
**Effort:** 1-2 hours
**Impact:** Filter 30-40% of weak trades

**Description:**
Reject LLM decisions below confidence threshold. Currently accepting 0.60-0.72 confidence trades which have poor success rate.

**Acceptance Criteria:**
- [ ] Add `--min-confidence` CLI argument
- [ ] Filter decisions in validation loop
- [ ] Test thresholds: 0.75, 0.80, 0.85
- [ ] Log rejected low-confidence trades
- [ ] Measure impact on trade frequency and win rate

**Technical Details:**
- File: `pacifica_agent/bot_pacifica.py:416-483`
- Add parameter to `__init__` and validation
- Track filtered trades for analysis

---

#### REQ-1.3: Reduced Trading Frequency
**Priority:** 🟡 MEDIUM
**Effort:** 5 minutes (config change)
**Impact:** 50-83% fee reduction

**Description:**
Reduce check interval to cut fee burn while maintaining meaningful volume.

**Options:**
- 10 min intervals: 50% fee reduction, 50% volume
- 15 min intervals: 67% fee reduction, 33% volume
- 30 min intervals: 83% fee reduction, 17% volume

**Acceptance Criteria:**
- [ ] Test each interval in dry-run
- [ ] Measure volume vs profitability trade-off
- [ ] Confirm minimum volume for points farming
- [ ] Deploy optimal interval

---

#### REQ-1.4: Fix Balance Fetching
**Priority:** 🟡 MEDIUM
**Effort:** 1-2 hours
**Impact:** Enable dynamic position sizing

**Description:**
Currently getting `WARNING: Could not fetch balance - using default position sizing`. This prevents intelligent position sizing based on account equity.

**Acceptance Criteria:**
- [ ] Debug `_fetch_account_balance()` failure
- [ ] Test `self.sdk.get_balance()` directly
- [ ] Add detailed error logging
- [ ] Verify API response format
- [ ] Enable dynamic sizing once working

**Technical Details:**
- File: `pacifica_agent/execution/pacifica_executor.py:57-68`
- Issue: Method returns None, falls back to hardcoded $375

---

### REQ-2: Additional Indicators Research

#### REQ-2.1: Evaluate Current Data Sources
**Priority:** 🟡 MEDIUM
**Effort:** 4-8 hours
**Impact:** Identify gaps in decision-making data

**Description:**
Analyze whether current indicators (RSI, MACD, EMAs, funding rates, OI, volume) provide enough actionable data for LLM decisions.

**Questions to Answer:**
- Is RSI "overbought" alone sufficient for short entry?
- Do we need volatility indicators (ATR, Bollinger Bands)?
- Should we add momentum indicators (Stochastic, CCI)?
- Are volume patterns useful (VWAP, OBV, volume profile)?
- Can on-chain data improve decisions (holder concentration, DEX flows)?

**Acceptance Criteria:**
- [ ] Document current indicator usage and gaps
- [ ] Research additional indicators from literature
- [ ] Test indicator combinations on historical data
- [ ] Measure predictive power of each indicator
- [ ] Recommend top 3-5 indicators to add

**Research Areas:**
1. **Technical Indicators:** ATR, Bollinger Bands, Stochastic, CCI, OBV, VWAP
2. **On-Chain Data:** Holder concentration, DEX flows, liquidity depth
3. **Market Microstructure:** Order flow, trade aggressiveness, liquidity imbalance
4. **Alternative Data:** Social sentiment trends, whale wallet activity
5. **Cross-Asset Signals:** BTC dominance, DXY, VIX correlation

---

#### REQ-2.2: Identify New Data Sources
**Priority:** 🟡 MEDIUM
**Effort:** 6-12 hours
**Impact:** Expand decision-making context

**Description:**
Find and integrate additional live data sources beyond current Pacifica, Cambrian, and Deep42 APIs.

**Potential Sources:**
- [ ] CoinGlass (funding rates, OI, liquidations)
- [ ] Glassnode (on-chain metrics)
- [ ] Santiment (social sentiment, dev activity)
- [ ] Messari (institutional flows, token unlocks)
- [ ] Alternative.me (Fear & Greed Index)
- [ ] DeFiLlama (TVL, protocol metrics)

**Acceptance Criteria:**
- [ ] Test API access and rate limits
- [ ] Evaluate data freshness and reliability
- [ ] Measure predictive value on historical trades
- [ ] Estimate cost (API fees)
- [ ] Integrate top 2-3 sources

---

### REQ-3: Microsoft Agent Lightning Integration

#### REQ-3.1: Clone and Setup
**Priority:** 🟢 RESEARCH
**Effort:** 1-2 hours
**Impact:** Foundation for advanced strategies

**Description:**
Clone Microsoft's Agent Lightning repo in a clearly marked temporary directory for research and testing.

**Acceptance Criteria:**
- [ ] Clone to `research/agent-lightning-TEST/` (marked temporary)
- [ ] Review README and architecture docs
- [ ] Identify dependencies and requirements
- [ ] Set up Python environment for testing
- [ ] Document repo structure and key components

**Safety Requirements:**
- ⚠️ Do NOT modify any live bot code
- ⚠️ Keep Agent Lightning isolated in research folder
- ⚠️ Clearly mark all test code as temporary
- ⚠️ Document everything for easy cleanup

---

#### REQ-3.2: Architecture Analysis
**Priority:** 🟢 RESEARCH
**Effort:** 8-16 hours
**Impact:** Understand applicable strategies

**Description:**
Deep-dive Agent Lightning codebase to identify strategies applicable to high-volume crypto trading.

**Analysis Areas:**
- [ ] Agent architecture and decision-making logic
- [ ] Strategy patterns and trading rules
- [ ] Risk management approaches
- [ ] Portfolio optimization techniques
- [ ] Multi-agent coordination (if applicable)
- [ ] Backtesting framework and methodology

**Deliverable:**
- Document: `research/AGENT_LIGHTNING_ARCHITECTURE.md`
- Sections: Overview, Key Components, Applicable Strategies, Integration Recommendations

---

#### REQ-3.3: Historical Data Backtesting
**Priority:** 🟢 RESEARCH
**Effort:** 12-24 hours
**Impact:** Validate strategies on real data

**Description:**
Test Agent Lightning strategies using 90 days of historical OHLCV data from Cambrian API and actual bot trade history.

**Test Data:**
- [ ] Fetch 90 days OHLCV from Cambrian (BTC, SOL, ETH, DOGE)
- [ ] Use Pacifica trade history (348 closed trades)
- [ ] Use Lighter trade history
- [ ] Include funding rates, OI, volume data

**Test Scenarios:**
- Scenario A: Agent Lightning default strategies
- Scenario B: Modified strategies for high-volume
- Scenario C: Hybrid (Agent Lightning + Deep42 sentiment)
- Scenario D: Multi-timeframe analysis (5min, 15min, 1h, 4h)

**Success Metrics:**
- Win rate improvement
- Sharpe ratio
- Max drawdown
- Volume maintained
- Fee efficiency

**Deliverable:**
- Report: `research/AGENT_LIGHTNING_BACKTEST_RESULTS.md`
- Test code: `research/agent-lightning-TEST/backtests/`

---

#### REQ-3.4: Integration Recommendations
**Priority:** 🟢 RESEARCH
**Effort:** 4-8 hours
**Impact:** Roadmap for implementation

**Description:**
Based on backtest results, create detailed integration plan for most promising Agent Lightning features.

**Deliverable:**
- Document: `research/AGENT_LIGHTNING_INTEGRATION_PLAN.md`
- Sections:
  - Top 3-5 recommended strategies
  - Implementation effort estimates
  - Expected performance improvements
  - Integration approach (incremental rollout)
  - Risk assessment and rollback plan

---

### REQ-4: Testing Infrastructure

#### REQ-4.1: Parallel Dry-Run Testing
**Priority:** 🔴 HIGH
**Effort:** 2-4 hours
**Impact:** Safe validation before deployment

**Description:**
Run 3 parallel dry-run bots to test improvements without risking capital.

**Test Configurations:**
- **Test A:** Higher confidence only (0.80+)
- **Test B:** Deep42 sentiment filter + confidence 0.75+
- **Test C:** 15min intervals + sentiment filter

**Acceptance Criteria:**
- [ ] Run each test for 24-48 hours
- [ ] Log all decisions and simulated trades
- [ ] Track metrics: win rate, volume, simulated P&L, fee costs
- [ ] Compare against live bot performance
- [ ] Create comparison report

**Technical Details:**
- Use `--dry-run` flag
- Separate log files: `logs/test_a.log`, `logs/test_b.log`, `logs/test_c.log`
- Save results: `research/testing/test_results_YYYYMMDD.json`

---

#### REQ-4.2: Automated Test Result Analysis
**Priority:** 🟡 MEDIUM
**Effort:** 4-6 hours
**Impact:** Data-driven deployment decisions

**Description:**
Create script to automatically analyze and compare test results.

**Features:**
- [ ] Parse dry-run logs
- [ ] Calculate win rate, Sharpe, max drawdown
- [ ] Compare fee costs across configurations
- [ ] Generate markdown report with charts
- [ ] Recommend best configuration

**Deliverable:**
- Script: `scripts/analyze_test_results.py`
- Report: `research/testing/TEST_COMPARISON_YYYYMMDD.md`

---

## 📁 File Structure

### New Files to Create

```
research/
├── PRD_BOT_PROFITABILITY_2025.md          # ✅ This file
├── PROGRESS_TRACKER.md                     # 🚧 Daily progress log
├── PACIFICA_PROFITABILITY_ANALYSIS.md      # ✅ Already created
├── ADDITIONAL_INDICATORS_RESEARCH.md       # 🔜 REQ-2.1
├── NEW_DATA_SOURCES_ANALYSIS.md           # 🔜 REQ-2.2
├── AGENT_LIGHTNING_ARCHITECTURE.md         # 🔜 REQ-3.2
├── AGENT_LIGHTNING_BACKTEST_RESULTS.md    # 🔜 REQ-3.3
├── AGENT_LIGHTNING_INTEGRATION_PLAN.md    # 🔜 REQ-3.4
│
├── agent-lightning-TEST/                   # 🔜 REQ-3.1
│   ├── README_TEMPORARY.md                # "THIS IS A TEMPORARY RESEARCH CLONE"
│   ├── .git/                              # Cloned repo
│   ├── backtests/                         # Custom backtest code
│   └── results/                           # Backtest results
│
└── testing/
    ├── test_results_20251108.json         # 🔜 REQ-4.1
    └── TEST_COMPARISON_20251108.md        # 🔜 REQ-4.2

scripts/
├── analyze_test_results.py                 # 🔜 REQ-4.2
└── fetch_historical_data.py                # 🔜 REQ-3.3
```

### Files to Modify

**⚠️ CAUTION: Test in dry-run first!**

```
pacifica_agent/
├── bot_pacifica.py                         # REQ-1.2 (confidence filtering)
└── execution/
    └── pacifica_executor.py                # REQ-1.1 (sentiment filtering)
                                           # REQ-1.4 (balance fix)
```

---

## 🗓️ Timeline

### Phase 1: Immediate Fixes (Days 1-2)
- ✅ Complete PRD (REQ-0)
- [ ] Create progress tracker
- [ ] Implement Deep42 sentiment filtering (REQ-1.1)
- [ ] Add confidence threshold (REQ-1.2)
- [ ] Fix balance fetching (REQ-1.4)
- [ ] Start parallel dry-run tests (REQ-4.1)

### Phase 2: Testing & Validation (Days 2-4)
- [ ] Run tests for 24-48 hours
- [ ] Analyze results (REQ-4.2)
- [ ] Deploy optimal config to live bot
- [ ] Monitor live performance

### Phase 3: Research (Days 2-7, parallel)
- [ ] Clone Agent Lightning (REQ-3.1)
- [ ] Architecture analysis (REQ-3.2)
- [ ] Additional indicators research (REQ-2.1, REQ-2.2)
- [ ] Fetch 90 days historical data (REQ-3.3)
- [ ] Run Agent Lightning backtests (REQ-3.3)
- [ ] Create integration plan (REQ-3.4)

### Phase 4: Long-term Improvements (Future)
- [ ] Implement Agent Lightning strategies
- [ ] Add new indicators
- [ ] Integrate new data sources
- [ ] Advanced risk management
- [ ] Multi-bot coordination

---

## 📊 Success Metrics

### Short-term (Week 1)
- [ ] Win rate >15% (from 6.1%)
- [ ] Daily fee burn <$80 (from $160)
- [ ] Break-even or positive daily P&L
- [ ] Volume maintained >$50k/day

### Medium-term (Month 1)
- [ ] Win rate >25%
- [ ] Sharpe ratio >0.5
- [ ] Monthly profit >$50
- [ ] Max drawdown <10%

### Long-term (Month 3)
- [ ] Win rate >40%
- [ ] Sharpe ratio >1.0
- [ ] Monthly profit >$200
- [ ] Fully autonomous operation

---

## ⚠️ Risks & Mitigation

### Risk 1: Testing Breaks Live Bot
**Probability:** Medium
**Impact:** High
**Mitigation:**
- ✅ Use dry-run flag for all testing
- ✅ Never modify live bot code directly
- ✅ Test changes in parallel environment
- ✅ Deploy only after 24-48 hours validation

### Risk 2: Context Window Exhaustion
**Probability:** High
**Impact:** Medium
**Mitigation:**
- ✅ Comprehensive PRD and progress tracker
- ✅ All work documented in markdown files
- ✅ Clear file naming and organization
- ✅ Git commits at each milestone

### Risk 3: Agent Lightning Incompatible
**Probability:** Medium
**Impact:** Low
**Mitigation:**
- ✅ Research-only phase first
- ✅ Backtest before integration
- ✅ Fallback to manual improvements
- ✅ No live code changes until validated

### Risk 4: Volume Drop Too Much
**Probability:** Medium
**Impact:** High (points farming)
**Mitigation:**
- ✅ Test multiple interval configurations
- ✅ Define minimum volume threshold
- ✅ Balance profitability vs volume
- ✅ User approval before volume reduction

---

## 📝 Progress Tracking

**See:** `research/PROGRESS_TRACKER.md` (updated daily)

**Format:**
```markdown
## 2025-11-08
- [x] Created PRD
- [ ] Task X in progress...
- [ ] Task Y completed
```

---

## 🔗 References

- [Pacifica Profitability Analysis](./PACIFICA_PROFITABILITY_ANALYSIS.md)
- [Pacifica Account Summary](./pacifica/ACCOUNT_SUMMARY.md)
- [Microsoft Agent Lightning](https://github.com/microsoft/agent-lightning)
- [Cambrian API Docs](https://docs.cambrian.org/)
- [Deep42 API Docs](https://deep42.cambrian.network/)

---

**Last Updated:** 2025-11-08 20:15 UTC
**Next Review:** 2025-11-09 (after first test results)
