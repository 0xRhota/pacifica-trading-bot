# Bots

Live trading bots that execute strategies on DEXes.

## Active Bots

### `vwap_lighter_bot.py`
VWAP + Orderbook strategy on Lighter DEX
- **Symbols**: BTC, SOL, ETH, PENGU, XPL, ASTER (6 total)
- **Strategy**: Long when price > VWAP + bid pressure, Short when price < VWAP + sell pressure
- **Check Frequency**: Every 5 minutes (288 cycles/day)
- **Position Size**: $20 per trade
- **Stop Loss**: 1%
- **Take Profit**: 2.5%
- **Expected Volume**: ~$7,200/day

**Launch**:
```bash
python3 bots/vwap_lighter_bot.py
# Or background:
nohup python3 -u bots/vwap_lighter_bot.py > vwap_bot_output.log 2>&1 &
```

## Adding New Bots

1. Create new bot file in this directory
2. Import from root: `from pacifica_bot import PacificaAPI`
3. Import strategies: `from strategies.vwap_strategy import VWAPStrategy`
4. Import DEX SDKs: `from dexes.lighter.lighter_sdk import LighterSDK`
5. Add path append: `sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))`
6. Update this README with bot details
