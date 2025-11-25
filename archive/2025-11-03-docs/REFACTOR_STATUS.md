# Refactor Status - Starting Fresh

## Current Status: Phase 1 Complete ✅

**Fixed**: Market mapping issue
- Created `dexes/lighter/adapter.py` that fetches markets dynamically from exchange
- No more hardcoded `{1: BTC, 2: SOL, 3: ETH, ...}` mapping
- Real mapping: `BTC=1, SOL=2, DOGE=3, WIF=5, XPL=71, ETH=0, PENGU=47, ASTER=83`

## Next Steps

### Immediate (Do Now)
1. ✅ Create Lighter adapter with dynamic market fetching
2. ⏳ Update Lighter bot to use adapter (test with real positions)
3. ⏳ Verify bot only sees positions that actually exist
4. ⏳ Create unified core architecture

### Architecture (After Fix)
1. Create `core/` - unified bot logic
2. Create `strategies/` - plug & play strategies
3. Create `bots/` - thin wrappers
4. Archive old files
5. Clean repo

## Key Principle: NO HARDCODING

- Markets: Fetch from exchange ✅
- Positions: Use real API data ✅
- Decisions: LLM makes them ✅
- Validation: Minimal (balance, max positions) ✅

## Testing

Once adapter is integrated:
- Bot should see only real positions (BTC, WIF, SOL, DOGE if they exist)
- No more "ETH" or "XPL" hallucinations
- Accurate logs showing real symbols


