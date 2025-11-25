# Deep42 Multi-Timeframe Implementation - Test Plan

**Date**: 2025-11-12
**Status**: TEST PHASE - Not affecting live bot

---

## CURRENT STATE (Confirmed from Code)

### What's Currently Working

**File**: `lighter_agent/bot_lighter.py`
- Line 99: `macro_refresh_hours=12` (now changed to 6 hours based on earlier session)
- Line 376-381: V1 prompt fetches `macro_context` which contains Deep42
- Line 428: `deep42_context=None` (this parameter exists but unused)

**File**: `llm_agent/llm/prompt_formatter.py` (V1)
- Line 188: Requires `macro_context` parameter (contains Deep42)
- Line 191: Accepts optional `deep42_context` parameter (not currently used)
- Line 246-247: Inserts macro_context into prompt (includes Deep42)

**File**: `llm_agent/data/macro_fetcher.py`
- Line 44-74: `_fetch_deep42_analysis()` method
- Line 203-238: `get_macro_context()` calls Deep42 with single question
- Currently asks: "What is the current state of the crypto market?"
- Refreshes every 6 hours (was 12h, changed earlier today)

**File**: `config_prompts.py`
- Line 21: `ACTIVE_PROMPT_VERSION = "v1_original"` (using V1 for Lighter)
- V1 includes Deep42 via macro_context

### Current Deep42 Integration

✅ **CONFIRMED WORKING**:
- Deep42 IS currently being used via `macro_context`
- Single broad question every 6 hours
- Inserted into V1 prompt at line 246-247
- LLM sees this context when making decisions

### What's NOT Being Used

❌ **NOT USED**:
- Multi-timeframe queries (1h regime, 4h BTC health)
- `deep42_context` parameter (exists but set to None)
- Specific volume farming instructions in prompt

---

## PROPOSED CHANGES (Minimal)

### Change 1: Add Multi-Timeframe Methods to `macro_fetcher.py`

**New Methods** (~60 lines total):
```python
def get_regime_context(self, force_refresh: bool = False) -> str:
    """Get hourly regime check (1h cache)"""

def get_btc_health(self, force_refresh: bool = False) -> str:
    """Get BTC health check (4h cache)"""

def get_enhanced_context(self, force_refresh: bool = False) -> Dict[str, str]:
    """Get all three contexts (combines macro, regime, BTC)"""
    return {
        "macro": self.get_macro_context(force_refresh),
        "regime": self.get_regime_context(force_refresh),
        "btc_health": self.get_btc_health(force_refresh)
    }
```

**Questions**:
- **Hourly (regime)**: "Is the crypto market currently in risk-on or risk-off mode? What should traders focus on right now?"
- **4-hour (BTC)**: "Should I be long or short Bitcoin right now based on price action, sentiment, and on-chain data?"
- **6-hour (macro)**: "What is the current state of the crypto market?" (UNCHANGED)

---

### Change 2: Enable Enhanced Context in `bot_lighter.py`

**Current** (line 428):
```python
prompt_kwargs["deep42_context"] = None  # NO Deep42 for Lighter bot
```

**Proposed**:
```python
# Get enhanced Deep42 context (multi-timeframe)
enhanced_deep42 = self.aggregator.get_enhanced_context()
prompt_kwargs["deep42_context"] = enhanced_deep42
```

---

### Change 3: Format Enhanced Context in `prompt_formatter.py`

**Current** (line 232-234):
```python
if deep42_context:
    sections.append(deep42_context)
    sections.append("")
```

**Proposed**:
```python
if deep42_context and isinstance(deep42_context, dict):
    sections.append("=" * 80)
    sections.append("DEEP42 MARKET INTELLIGENCE (Multi-Timeframe)")
    sections.append("=" * 80)
    sections.append("")

    if "regime" in deep42_context:
        sections.append("MARKET REGIME (Updated Hourly):")
        sections.append(deep42_context["regime"])
        sections.append("")

    if "btc_health" in deep42_context:
        sections.append("BTC HEALTH INDICATOR (Updated Every 4h):")
        sections.append(deep42_context["btc_health"])
        sections.append("")

    if "macro" in deep42_context:
        sections.append("MACRO CONTEXT (Updated Every 6h):")
        sections.append(deep42_context["macro"])
        sections.append("")

    sections.append("=" * 80)
    sections.append("USE THIS CONTEXT TO:")
    sections.append("- FILTER out trap trades (risk-off + low quality social = skip)")
    sections.append("- ADJUST confidence (risk-on = higher, risk-off = lower)")
    sections.append("- AVOID altcoin longs when BTC is bearish")
    sections.append("=" * 80)
    sections.append("")
elif deep42_context:
    # Fallback for string format (backward compatible)
    sections.append(deep42_context)
    sections.append("")
```

---

### Change 4: Update Prompt Instructions (Volume + Profit Focus)

**Add to instructions section** (around line 300 in prompt_formatter.py):
```python
**YOUR MISSION (Lighter DEX - Fee-Less zkSync Exchange):**

PRIMARY GOAL: Generate profitable trades
- Target 55%+ win rate with 2:1 risk/reward minimum
- Strict stop losses at -1% to -2%
- Let winners run to 2-4% profit targets
- Quality setups only - avoid marginal trades

SECONDARY GOAL: Generate volume for airdrop eligibility
- Target 40-50 quality trades per day
- Fee-less exchange = no cost to trade
- But NEVER sacrifice profitability for volume
- Bad trades hurt more than missing volume helps

**HOW TO USE DEEP42 CONTEXT:**

MARKET REGIME (Hourly):
- Risk-ON: Can be more aggressive with entries, slightly higher confidence
- Risk-OFF: Be selective, only take A-grade setups, lower confidence on marginal setups

BTC HEALTH (4-hour):
- BTC Bullish: Favor altcoin longs (market leader strong = alts follow)
- BTC Bearish: Avoid altcoin longs (BTC weakness drags everything down)
- BTC Neutral: Focus on token-specific setups (less market correlation risk)

MACRO CONTEXT (6-hour):
- Understand overall narrative (AI-blockchain, regulations, catalysts)
- Identify themes to focus on or avoid

**DEEP42 QUALITY SCORES (Social Sentiment):**
- Score 7-10: High quality, organic interest, credible sources → TRUST the setup
- Score 5-7: Mixed signals, some organic interest → CAUTION, verify with technicals
- Score 1-5: Low quality, likely pump-and-dump, coordinated promotion → AVOID entirely

**YOUR DECISION PHILOSOPHY:**
- When setup is excellent + Deep42 confirms: HIGH CONFIDENCE (0.7-0.9)
- When setup is good but Deep42 warns (risk-off, low quality score): LOWER CONFIDENCE (0.5-0.6)
- When setup is marginal: SKIP (quality over quantity)
- When Deep42 shows pump-and-dump pattern (quality <5): SKIP (avoid catastrophic loss)

Deep42 helps you FILTER bad trades, not prevent all risk-taking.
Your job is to make profitable trades while generating volume.
```

---

## TEST IMPLEMENTATION

### Test Script: `scripts/test_deep42_integration.py`

**Purpose**: Test multi-timeframe Deep42 queries WITHOUT affecting live bot

```python
#!/usr/bin/env python3
"""
Test Deep42 Multi-Timeframe Integration
Tests new Deep42 methods without affecting live bot
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add parent to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_agent.data.macro_fetcher import MacroContextFetcher

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

logger = logging.getLogger(__name__)


async def test_deep42_multi_timeframe():
    """Test multi-timeframe Deep42 queries"""

    cambrian_api_key = os.getenv("CAMBRIAN_API_KEY")
    if not cambrian_api_key:
        logger.error("CAMBRIAN_API_KEY not found in .env")
        return

    logger.info("=" * 80)
    logger.info("DEEP42 MULTI-TIMEFRAME INTEGRATION TEST")
    logger.info("=" * 80)
    logger.info("")

    # Initialize fetcher
    fetcher = MacroContextFetcher(
        cambrian_api_key=cambrian_api_key,
        refresh_interval_hours=6
    )

    # Test 1: Current macro context (6h)
    logger.info("TEST 1: Current Macro Context (6h refresh)")
    logger.info("-" * 80)
    macro = fetcher.get_macro_context(force_refresh=True)
    logger.info(macro)
    logger.info("")

    # Test 2: Regime context (1h) - NEW
    logger.info("TEST 2: Market Regime Context (1h refresh) - NEW")
    logger.info("-" * 80)
    if hasattr(fetcher, 'get_regime_context'):
        regime = fetcher.get_regime_context(force_refresh=True)
        logger.info(regime)
    else:
        logger.warning("⚠️ get_regime_context() not implemented yet")
    logger.info("")

    # Test 3: BTC health (4h) - NEW
    logger.info("TEST 3: BTC Health Indicator (4h refresh) - NEW")
    logger.info("-" * 80)
    if hasattr(fetcher, 'get_btc_health'):
        btc = fetcher.get_btc_health(force_refresh=True)
        logger.info(btc)
    else:
        logger.warning("⚠️ get_btc_health() not implemented yet")
    logger.info("")

    # Test 4: Enhanced context (all three) - NEW
    logger.info("TEST 4: Enhanced Context (All Three Combined) - NEW")
    logger.info("-" * 80)
    if hasattr(fetcher, 'get_enhanced_context'):
        enhanced = fetcher.get_enhanced_context(force_refresh=True)
        logger.info(f"Keys: {list(enhanced.keys())}")
        for key, value in enhanced.items():
            logger.info(f"\n{key.upper()}:")
            logger.info(value[:200] + "..." if len(value) > 200 else value)
    else:
        logger.warning("⚠️ get_enhanced_context() not implemented yet")
    logger.info("")

    logger.info("=" * 80)
    logger.info("TEST COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_deep42_multi_timeframe())
```

**Run Test**:
```bash
python scripts/test_deep42_integration.py
```

---

## IMPLEMENTATION CHECKLIST

### Phase 1: Add Methods (No Live Bot Impact)
- [ ] Add `get_regime_context()` to `macro_fetcher.py`
- [ ] Add `get_btc_health()` to `macro_fetcher.py`
- [ ] Add `get_enhanced_context()` to `macro_fetcher.py`
- [ ] Add caching for 1h and 4h intervals
- [ ] Test with `scripts/test_deep42_integration.py`

### Phase 2: Format Enhanced Context (No Live Bot Impact)
- [ ] Update `prompt_formatter.py` to handle dict `deep42_context`
- [ ] Add formatting for regime, BTC health, macro
- [ ] Add usage instructions section
- [ ] Keep backward compatibility (string format fallback)

### Phase 3: Update Prompt Instructions (No Live Bot Impact)
- [ ] Add volume + profit mission statement
- [ ] Add Deep42 usage guide (regime, BTC health, quality scores)
- [ ] Add decision philosophy section
- [ ] Emphasize profitable trades (not "stay even")

### Phase 4: Enable in Bot (CONTROLLED TEST)
- [ ] Update `bot_lighter.py` line 428 to use enhanced context
- [ ] Add logging: "Using Deep42 multi-timeframe context"
- [ ] Monitor logs for LLM responses mentioning Deep42
- [ ] Track: Does LLM reference regime/BTC health in reasoning?

### Phase 5: Validation (7-Day A/B Test)
- [ ] Deploy to Lighter bot WITH enhanced Deep42
- [ ] Keep Pacifica bot WITHOUT changes (control)
- [ ] Compare metrics:
  - Win rate (target: maintain 47% or improve to 50-52%)
  - Large losses >10% (target: reduce by 30-40%)
  - Trade frequency (target: maintain 40-50/day)
  - Deep42 usage rate (target: ≥30% of decisions mention it)

---

## ROLLBACK PLAN

If anything goes wrong:

**Step 1**: Disable enhanced context
```python
# In bot_lighter.py line 428
prompt_kwargs["deep42_context"] = None  # Rollback to single macro context only
```

**Step 2**: Restart bot
```bash
pkill -f "lighter_agent.bot_lighter"
nohup python3 -u -m lighter_agent.bot_lighter --live --interval 300 > logs/lighter_bot.log 2>&1 &
```

**Step 3**: Verify rollback
```bash
tail -100 logs/lighter_bot.log | grep "Deep42"
```

Should see: "NO Deep42 for Lighter bot" or only single macro context

---

## SUCCESS CRITERIA

**Minimum Success** (Deploy):
- ✅ Test script runs without errors
- ✅ All three Deep42 queries return valid responses
- ✅ Enhanced context formats correctly in prompt
- ✅ LLM references Deep42 in reasoning (≥30% of decisions)
- ✅ No increase in API errors or timeouts

**Ideal Success** (Keep Long-Term):
- ✅ Win rate improves 47% → 50-52%
- ✅ Large losses (>10%) reduced by 30-40%
- ✅ Trade frequency maintained at 40-50/day
- ✅ LLM reasoning quality visibly improves
- ✅ Cost increase acceptable (<$2/day additional)

**Failure Criteria** (Rollback):
- ❌ Win rate drops below 44%
- ❌ Large losses increase
- ❌ Trade frequency drops below 35/day
- ❌ LLM ignores Deep42 context entirely
- ❌ Deep42 API timeouts >20% of requests

---

**Next Step**: Implement Phase 1 (add methods to macro_fetcher.py) and run test script
