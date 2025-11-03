# Lighter Exchange API Key Registration: Documentation References

**Date**: 2025-10-31

---

## Official Documentation References

### 1. SDK/Programmatic Registration (ETH_PRIVATE_KEY Required)

**Source**: ["Get Started For Programmers"](https://apidocs.lighter.xyz/docs/get-started-for-programmers-1#/)

**Section**: "Setting up an API KEY"

**Quote**:
> "In order to get started using the Lighter API, you must first set up an **API_KEY_PRIVATE_KEY**, as you will need it to sign any transaction you want to make. You can find how to do it in the following example. The **BASE_URL** will reflect if your key is generated on testnet or mainnet (for mainnet, just change the **BASE_URL** in the example to https://mainnet.zklighter.elliot.ai). **Note that you also need to provide your ETH_PRIVATE_KEY.**"

**What this means**: For SDK/programmatic setup, ETH_PRIVATE_KEY is required for initial API key registration via `change_api_key()` method.

---

### 2. SignerClient Initialization (Only API Key Needed for Trading)

**Source**: Same page, ["The Signer" section](https://apidocs.lighter.xyz/docs/get-started-for-programmers-1#/)

**Code Example**:
```python
client = lighter.SignerClient(
    url=BASE_URL,
    private_key=API_KEY_PRIVATE_KEY,  # ← Only API key needed here
    account_index=ACCOUNT_INDEX,
    api_key_index=API_KEY_INDEX
)
```

**What this means**: Once API key is registered, SignerClient only needs `API_KEY_PRIVATE_KEY` for trading operations - ETH_PRIVATE_KEY is NOT used.

---

### 3. SDK Repositories

- **Python SDK**: https://github.com/elliottech/lighter-python
- **Go SDK**: https://github.com/elliottech/lighter-go

---

## Summary for Lighter Team

**Key Point**: The official documentation at https://apidocs.lighter.xyz/docs/get-started-for-programmers-1#/ states:

1. **ETH_PRIVATE_KEY is required** for SDK-based API key setup (programmatic registration)
2. **The docs only cover SDK setup** - they don't mention web UI registration
3. **After registration, SignerClient only needs API_KEY_PRIVATE_KEY** (no ETH key needed for trading)

**Conclusion**: 
- If registering API keys via **web UI** (`https://app.lighter.xyz`), ETH_PRIVATE_KEY is NOT needed
- If registering via **SDK programmatically**, ETH_PRIVATE_KEY IS required for `change_api_key()` function
- For **trading operations**, only API_KEY_PRIVATE_KEY is needed (regardless of registration method)

**Question for Lighter Team**: Can you confirm that API keys can be generated and registered entirely through https://app.lighter.xyz without any ETH_PRIVATE_KEY exposure? The docs only cover SDK setup, which requires ETH_PRIVATE_KEY.

---

## References from Repository

**Internal Scripts**:
- `scripts/lighter/register_lighter_api_key.py` (Line 16): `"""Register the API key you generated in Lighter UI"""`
- `scripts/lighter/find_lighter_api_key.py` (Line 71): `print("You'll need to register it through Lighter UI or with ETH key.")`

These scripts suggest two registration paths: UI (no ETH key) or programmatic (ETH key required).

