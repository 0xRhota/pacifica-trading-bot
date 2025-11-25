#!/usr/bin/env python3
"""
Clean trade tracker by syncing with API
Removes stale "open" positions that don't exist on exchange
"""

import os
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from trade_tracker import TradeTracker
import requests
from dotenv import load_dotenv

load_dotenv(project_root / ".env")

def clean_tracker():
    """Clean tracker to match actual API positions"""
    print("=" * 60)
    print("🧹 CLEANING TRADE TRACKER")
    print("=" * 60)
    
    account = os.getenv('PACIFICA_ACCOUNT')
    if not account:
        print("❌ PACIFICA_ACCOUNT not found in .env")
        return
    
    # Load tracker
    tracker = TradeTracker(dex="pacifica")
    tracker_open = tracker.get_open_trades()
    
    print(f"\n📊 Tracker shows {len(tracker_open)} 'open' positions")
    
    # Get actual API positions
    try:
        response = requests.get(
            "https://api.pacifica.fi/api/v1/positions",
            params={"account": account},
            timeout=10
        )
        
        if response.status_code == 200:
            api_positions = response.json()
            if not isinstance(api_positions, list):
                api_positions = []
            
            print(f"✅ API shows {len(api_positions)} actual open positions")
            
            # Build set of actual positions (symbol + side)
            actual_keys = set()
            for pos in api_positions:
                symbol = pos.get('symbol') or pos.get('market') or 'UNKNOWN'
                side = 'buy' if pos.get('side') == 'bid' else 'sell'
                actual_keys.add(f"{symbol}_{side}")
            
            # Find tracker positions that don't exist in API
            to_close = []
            for trade in tracker_open:
                symbol = trade.get('symbol')
                side = trade.get('side')
                key = f"{symbol}_{side}"
                
                if key not in actual_keys:
                    to_close.append(trade)
            
            print(f"\n🗑️  Found {len(to_close)} stale positions to close")
            
            if to_close:
                print("\nClosing stale positions:")
                for trade in to_close:
                    order_id = trade.get('order_id')
                    symbol = trade.get('symbol')
                    side = trade.get('side')
                    
                    if order_id:
                        # Close properly with order_id
                        tracker.log_exit(
                            order_id=order_id,
                            exit_price=trade.get('entry_price', 0),
                            exit_reason="Closed outside bot (sync)",
                            fees=0.0
                        )
                        print(f"  ✅ {symbol} {side} (order_id: {order_id})")
                    else:
                        # Mark as closed manually (no order_id = can't use log_exit)
                        trade['status'] = 'closed'
                        trade['exit_price'] = trade.get('entry_price', 0)
                        trade['exit_timestamp'] = trade.get('timestamp', '')
                        trade['exit_reason'] = 'Stale entry (cleaned)'
                        trade['pnl'] = 0.0
                        trade['pnl_pct'] = 0.0
                        trade['fees'] = 0.0
                        print(f"  ✅ {symbol} {side} (no order_id - manual close)")
                
                # Save updated trades
                tracker._save_trades()
                print(f"\n✅ Cleaned {len(to_close)} stale positions")
            else:
                print("\n✅ Tracker is in sync with API")
        else:
            print(f"❌ API error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Final stats
    print("\n" + "=" * 60)
    print("📊 FINAL STATS:")
    print("=" * 60)
    tracker.print_stats()

if __name__ == "__main__":
    clean_tracker()


