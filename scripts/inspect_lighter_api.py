"""
Inspect Lighter API methods to find correct parameters
"""

import lighter
import inspect

order_api = lighter.OrderApi(lighter.ApiClient())

print("=" * 80)
print("LIGHTER ORDER API METHOD SIGNATURES")
print("=" * 80)

methods = [
    'trades',
    'recent_trades',
    'export',
    'account_inactive_orders',
    'account_active_orders'
]

for method_name in methods:
    method = getattr(order_api, method_name)
    sig = inspect.signature(method)
    print(f"\n{method_name}{sig}")

    # Get docstring if available
    if method.__doc__:
        print(f"  Doc: {method.__doc__[:200]}")
