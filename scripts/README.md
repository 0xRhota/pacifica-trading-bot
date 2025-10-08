# Scripts

Testing and utility scripts organized by purpose.

## Structure

### `lighter/`
Lighter DEX testing and utility scripts:
- `check_account.py` - Check account details
- `check_balance.py` - Check account balance
- `explore_sdk.py` - Explore SDK capabilities
- `find_account_index.py` - Find account index
- `find_api_key.py` - Find API key
- `get_account_index.py` - Get account index
- `register_api_key.py` - Register API key
- `setup_api_key.py` - Setup API key
- `test_connection.py` - Test Lighter connection
- `test_order.py` - Test order placement
- `test_trade.py` - Test trade execution

### `pacifica/`
Pacifica DEX testing and utility scripts (to be added)

### `general/`
General utilities:
- `sync_tracker.py` - Sync trade tracker with exchange
- `place_order_now.py` - Manual order placement

## Usage

All scripts need path append for imports:
```python
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
```

Run from root:
```bash
python3 scripts/lighter/test_connection.py
python3 scripts/general/sync_tracker.py
```
