# Complete Bot Refactor Plan

## Core Principles

1. **No Hardcoding**: Fetch markets dynamically from exchange
2. **LLM-Driven**: LLM makes decisions, not hardcoded logic
3. **Plug & Play Strategies**: Easy to swap strategies
4. **Accurate Data**: Only show LLM what actually exists
5. **Clean Repo**: Remove experimental files, confusing notes

## Root Cause: Market Mapping Issue

**Problem**: Hardcoded `{1: BTC, 2: SOL, 3: ETH, 4: PENGU, 5: XPL, 6: ASTER}` is WRONG
- Actual positions: BTC, WIF, SOL, DOGE
- API returns market_ids that don't match our mapping
- Bot sees ETH/XPL because market_id 3/5 exist, but we mapped them wrong

**Solution**: Fetch markets from exchange, build mapping dynamically

## New Architecture

### Structure
```
core/
  ├── trading_bot.py          # Unified bot orchestrator
  ├── decision_engine.py      # LLM decision making (strategy-agnostic)
  ├── position_manager.py     # Position tracking (unified)
  └── logger.py               # Unified logging

dexes/
  ├── pacifica/
  │   ├── adapter.py          # Pacifica API: markets, positions, orders
  │   └── market_fetcher.py   # Pacifica market data
  └── lighter/
      ├── adapter.py          # Lighter API: markets, positions, orders  
      └── market_fetcher.py   # Lighter market data

strategies/
  ├── base_strategy.py        # Strategy interface
  ├── llm_strategy.py         # Current LLM-based strategy
  └── (future strategies)

bots/
  ├── pacifica_bot.py         # ~30 lines: loads core + Pacifica adapter
  └── lighter_bot.py          # ~30 lines: loads core + Lighter adapter
```

### Key Design Decisions

1. **Dynamic Market Discovery**
   - Fetch markets from exchange on startup
   - Build `market_id -> symbol` mapping from real data
   - Validate every position against actual markets

2. **LLM-First**
   - LLM sees all available markets
   - LLM sees all open positions (with accurate symbols)
   - LLM makes decisions, we execute them
   - No hardcoded "don't trade XPL" logic

3. **Strategy Interface**
   - `get_decisions(market_data, positions) -> decisions`
   - Easy to swap LLM strategy with other strategies
   - Strategy just returns decisions, bot executes

4. **Minimal Validation**
   - Check position exists on exchange: YES
   - Check we have balance: YES
   - Check max positions: YES
   - Everything else: LLM decides

## Implementation Steps

### Phase 1: Fix Market Mapping (Critical - Do First)
1. Add `get_markets()` to Lighter adapter - fetch from exchange
2. Build `market_id -> symbol` mapping dynamically
3. Use real mapping for all position lookups
4. Test: Bot should only see BTC, WIF, SOL, DOGE (what actually exists)

### Phase 2: Unified Core
1. Create `core/trading_bot.py` - main loop (unified)
2. Create `core/decision_engine.py` - LLM calls (strategy-agnostic)
3. Create `core/position_manager.py` - position tracking (unified)
4. Create `core/logger.py` - unified logging format

### Phase 3: DEX Adapters
1. Create `dexes/lighter/adapter.py`:
   - `get_markets()` - fetch from exchange
   - `get_positions()` - with correct symbol mapping
   - `place_order()` - order execution
2. Create `dexes/pacifica/adapter.py`:
   - Same interface as Lighter
   - Pacifica-specific implementation

### Phase 4: Strategy System
1. Create `strategies/base_strategy.py` - interface
2. Move LLM logic to `strategies/llm_strategy.py`
3. Bot uses strategy, doesn't care which one

### Phase 5: Clean Bots
1. `bots/pacifica_bot.py` - thin wrapper
2. `bots/lighter_bot.py` - thin wrapper
3. Both use same core + different adapters

### Phase 6: Cleanup
1. Archive old bot files
2. Remove experimental scripts
3. Remove confusing docs
4. Update README with new structure

## Files to Create

### Core (New)
- `core/trading_bot.py`
- `core/decision_engine.py`
- `core/position_manager.py`
- `core/logger.py`

### DEX Adapters (New)
- `dexes/lighter/adapter.py`
- `dexes/pacifica/adapter.py`

### Strategies (New)
- `strategies/base_strategy.py`
- `strategies/llm_strategy.py`

### Bots (New)
- `bots/pacifica_bot.py`
- `bots/lighter_bot.py`

## Files to Archive

- `llm_agent/bot_llm.py`
- `lighter_agent/bot_lighter.py`
- `llm_agent/execution/trade_executor.py`
- `lighter_agent/execution/lighter_executor.py`
- All experimental scripts in `scripts/`
- Confusing markdown files

## Files to Keep (Update)

- `llm_agent/llm/` - Use in strategy
- `llm_agent/data/` - Use in adapters
- `trade_tracker.py` - Update for unified system
- `config.py` - Simplify

## Validation

- [ ] Lighter bot only sees positions that actually exist
- [ ] Market mapping built from exchange (no hardcoding)
- [ ] Both bots work with same core
- [ ] LLM sees accurate data, makes decisions
- [ ] No hardcoded trading rules
- [ ] Clean repo, no experimental files
- [ ] Accurate logs, one format
