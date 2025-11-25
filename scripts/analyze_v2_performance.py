import json
from datetime import datetime

# Read current V2 trades
with open('logs/trades/lighter.json', 'r') as f:
    trades = json.load(f)

closed = [t for t in trades if t.get('status') == 'closed']

print(f'=== DEEP42-V2-PATIENT PERFORMANCE ===')
print(f'Total Closed Trades: {len(closed)}')
print()

# Calculate stats
wins = [t for t in closed if t.get('pnl', 0) > 0]
losses = [t for t in closed if t.get('pnl', 0) <= 0]

total_pnl = sum(t.get('pnl', 0) for t in closed)
avg_win = sum(t.get('pnl', 0) for t in wins) / len(wins) if wins else 0
avg_loss = sum(t.get('pnl', 0) for t in losses) / len(losses) if losses else 0
win_rate = len(wins) / len(closed) * 100 if closed else 0

print(f'Win Rate: {win_rate:.1f}% ({len(wins)}/{len(closed)})')
print(f'Total P&L: ${total_pnl:.4f}')
print(f'Avg Win: ${avg_win:.4f}')
print(f'Avg Loss: ${avg_loss:.4f}')
print(f'Risk/Reward: {abs(avg_win/avg_loss):.2f}:1' if avg_loss != 0 else 'N/A')
print()

# Check hold times
print('HOLD TIME ANALYSIS:')
hold_times = []
for t in closed:
    if t.get('timestamp') and t.get('exit_timestamp'):
        entry = datetime.fromisoformat(t['timestamp'])
        exit = datetime.fromisoformat(t['exit_timestamp'])
        minutes = (exit - entry).total_seconds() / 60
        hold_times.append(minutes)

if hold_times:
    avg_hold = sum(hold_times) / len(hold_times)
    under_30 = [h for h in hold_times if h < 30]
    print(f'  Avg Hold: {avg_hold:.1f} minutes')
    print(f'  <30 min: {len(under_30)} trades ({len(under_30)/len(hold_times)*100:.1f}%)')
    print(f'  ≥30 min: {len(hold_times) - len(under_30)} trades ({(len(hold_times)-len(under_30))/len(hold_times)*100:.1f}%)')
print()

# Analyze premature exits
print('PREMATURE EXIT ANALYSIS:')
tiny_profits = [t for t in wins if 0 < t.get('pnl', 0) < 0.10]
print(f'  Wins <$0.10: {len(tiny_profits)} trades ({len(tiny_profits)/len(wins)*100:.1f}%), ${sum(t.get("pnl", 0) for t in tiny_profits):.4f} total')
print()

# Check if bot is following instructions
print('BOT INSTRUCTION COMPLIANCE:')
early_exits = []
for t in closed:
    if t.get('timestamp') and t.get('exit_timestamp'):
        entry = datetime.fromisoformat(t['timestamp'])
        exit = datetime.fromisoformat(t['exit_timestamp'])
        minutes = (exit - entry).total_seconds() / 60
        pnl_pct = t.get('pnl_pct', 0) * 100 if t.get('pnl_pct') else 0

        # Check if closed early (< 30 min) without hitting stop loss or profit target
        if minutes < 30 and abs(pnl_pct) < 1.5:  # Not at stop loss (<-1%) or profit target (>1.5%)
            early_exits.append({
                'symbol': t['symbol'],
                'minutes': minutes,
                'pnl_pct': pnl_pct,
                'reason': t.get('exit_reason', '').replace('"', '')[:80]
            })

print(f'  Early Exits (<30 min, not stop/target): {len(early_exits)}')
if early_exits:
    print('  Examples:')
    for i, e in enumerate(early_exits[:5], 1):
        print(f'    {i}. {e["symbol"]}: {e["minutes"]:.0f}min, {e["pnl_pct"]:.2f}% - "{e["reason"]}"')
print()

# Compare to V1
print('=== COMPARISON TO V1 ===')
print('V1: 50.8% WR, $0.06 avg win, 11.7 min hold')
print(f'V2: {win_rate:.1f}% WR, ${avg_win:.4f} avg win, {avg_hold:.1f} min hold')
print()
if avg_hold < 20:
    print('❌ V2 WORSE: Hold time decreased further!')
elif avg_hold > 25:
    print('✅ V2 BETTER: Hold time improved')
else:
    print('⚠️  V2 MIXED: Slight improvement but still too short')
