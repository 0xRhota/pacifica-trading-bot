# Lighter DEX Integration Requirements

## API Documentation
- **Docs**: https://apidocs.lighter.xyz/docs/get-started-for-programmers-1
- **SDK**: https://github.com/elliottech/lighter-python
- **Python Version**: 3.8+

## Installation
```bash
pip install git+https://github.com/elliottech/lighter-python.git
```

## Authentication

### Required Keys
```bash
# .env
ETH_PRIVATE_KEY=your_ethereum_private_key_here
LIGHTER_API_KEY_PRIVATE_KEY=638995bed741b84f3cd552cac0a00222440acab5d1a67bbe88926979ba4a4de61e133aab4f53696e
```

### API Key System
- Can create up to **253 API keys** (indexes 2-254)
- Reserved indexes:
  - 0: Desktop
  - 1: Mobile
  - 255: Retrieve all API key data
- Each API key has its own index for signing

## SDK Initialization

### SignerClient (for placing orders)
```python
import lighter
from lighter import SignerClient

client = SignerClient(
    url=BASE_URL,
    private_key=API_KEY_PRIVATE_KEY,  # Your Lighter API key
    account_index=ACCOUNT_INDEX,
    api_key_index=API_KEY_INDEX
)
```

### ApiClient (for market data)
```python
client = lighter.ApiClient()
account_api = lighter.AccountApi(client)
order_api = lighter.OrderApi(client)
```

## Base URLs

### Mainnet
```
https://mainnet.zklighter.elliot.ai
```

### Testnet
Use default URL in SDK (check SDK source for exact URL)

## Order Types

### Market Order
```python
await client.create_market_order(
    base_amount=100,        # Integer (token units)
    price=2000,             # Integer (in smallest denomination)
    client_order_index=1,   # Unique identifier
    order_type=ORDER_TYPE_MARKET,
    time_in_force=TIME_IN_FORCE_IOC  # Immediate or Cancel
)
```

### Limit Order
```python
await client.create_order(
    base_amount=100,
    price=2000,
    client_order_index=2,
    order_type=ORDER_TYPE_LIMIT,
    time_in_force=TIME_IN_FORCE_GTC  # Good Till Cancelled
)
```

### Other Order Types
- **Stop Loss**: Triggers at specific price
- **Take Profit**: Closes at profit target
- **TWAP**: Time-weighted average price

## Time-in-Force Options
- **IOC**: Immediate or Cancel
- **GTT**: Good Till Time
- **POST_ONLY**: Only maker orders (no taker fees)

## Order Management

### Cancel Order
```python
await client.create_cancel_order(
    client_order_index=1
)
```

### Cancel All Orders
```python
await client.cancel_all_orders()
```

## Nonce Management
Every transaction requires incrementing nonce:
```python
from lighter import TransactionApi

nonce = await TransactionApi.next_nonce()
```

## Account Types

### Standard Account (Fee-less)
- No trading fees
- Default account type

### Premium Account
- 0.2 bps maker fee
- 2 bps taker fee
- Better for high-frequency trading

## Key Differences from Pacifica

| Feature | Pacifica | Lighter |
|---------|----------|---------|
| Blockchain | Solana | zkSync (Ethereum L2) |
| SDK Style | Sync (requests) | Async (asyncio) |
| Auth | Solana signature | ETH + API key |
| Order Size | Float (0.05 SOL) | Integer (100 units) |
| Private Key | SOLANA_PRIVATE_KEY | ETH_PRIVATE_KEY + LIGHTER_API_KEY_PRIVATE_KEY |
| Signature | Ed25519 | ECDSA (Ethereum) |

## SDK Modules

### Core APIs
- **AccountApi**: Account information, balances
- **BlockApi**: Block data
- **OrderApi**: Order placement and management
- **TransactionApi**: Transaction handling, nonce management

### Key Classes
- **SignerClient**: For placing orders (requires private key)
- **ApiClient**: For reading data (no auth needed)

## Async Pattern
All SDK methods are async:
```python
import asyncio

async def main():
    client = lighter.SignerClient(...)
    result = await client.create_market_order(...)
    print(result)

asyncio.run(main())
```

## Order Size Handling

### Pacifica (Current)
```python
size = 0.05  # 0.05 SOL
price = 233.50
value = size * price  # $11.68
```

### Lighter (New)
```python
# Lighter uses integer amounts
base_amount = 100  # Integer units
price = 233500      # Price in smallest denomination (cents/wei)
# Need to understand token decimals
```

**TODO**: Confirm Lighter token decimal handling

## Position Tracking

### Get Positions
```python
positions = await client.get_positions()
# Returns list of open positions
```

### Get Account Balance
```python
account = await account_api.get_account(by="index", value="1")
balance = account.balance
```

## WebSocket Support
Lighter SDK includes WebSocket client for real-time updates:
- Price feeds
- Order book updates
- Position changes

**TODO**: Explore WebSocket integration for position monitoring

## Error Handling
```python
try:
    result = await client.create_market_order(...)
except lighter.ApiException as e:
    print(f"API error: {e}")
except Exception as e:
    print(f"Error: {e}")
```

## Testing Checklist

### Setup
- [ ] Install lighter-python SDK
- [ ] Generate ETH_PRIVATE_KEY
- [ ] Create API key on Lighter
- [ ] Test connection to testnet
- [ ] Verify account creation

### Basic Operations
- [ ] Get account balance
- [ ] Get market price for BTC/ETH/SOL
- [ ] Place test market order on testnet
- [ ] Cancel order
- [ ] Get open positions

### Integration
- [ ] Wrap async SDK in DEXAdapter interface
- [ ] Convert position size USD → base_amount
- [ ] Handle integer pricing
- [ ] Test error handling
- [ ] Verify nonce management

## Questions to Research

1. **Token Decimals**: How does Lighter handle decimals for different tokens?
2. **Symbol Format**: What's the exact format? (BTC-PERP? BTC/USD? BTC?)
3. **Minimum Order Size**: What's the minimum $USD value per order?
4. **Lot Size**: Is there a lot size increment like Pacifica's 0.01?
5. **Leverage**: How is leverage specified in orders?
6. **Liquidation**: How do we get liquidation price?
7. **Fees**: Confirm fee structure for mainnet
8. **Rate Limits**: Are there API rate limits?

## Next Steps

1. Install SDK and test basic connection
2. Create test account on Lighter testnet
3. Place one test order manually
4. Document actual API responses
5. Map Lighter API to DEXAdapter interface
6. Write LighterAdapter class
7. Test with small positions on testnet
8. Compare behavior with Pacifica

## Resources
- SDK Examples: https://github.com/elliottech/lighter-python/tree/main/examples
- API Docs: https://apidocs.lighter.xyz
- Whitepaper: https://docs.lighter.xyz (technical architecture)
