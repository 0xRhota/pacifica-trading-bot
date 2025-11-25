import json
from datetime import datetime

# Read archived trades from deep42-v1 (the 198 trades before v2)
with open('logs/trades/archive/lighter_deep42-v2-patient_20251114_104548.json', 'r') as f:
    archived = json.load(f)

# Get closed trades only
closed = [t for t in archived if t.get('status') == 'closed']

print(f'Total Trades: {len(closed)}')
print()

# Calculate stats
wins = [t for t in closed if t.get('pnl', 0) > 0]
losses = [t for t in closed if t.get('pnl', 0) < 0]

total_pnl = sum(t.get('pnl', 0) for t in closed)
avg_win = sum(t.get('pnl', 0) for t in wins) / len(wins) if wins else 0
avg_loss = sum(t.get('pnl', 0) for t in losses) / len(losses) if losses else 0
win_rate = len(wins) / len(closed) * 100 if closed else 0

print(f'Win Rate: {win_rate:.1f}% ({len(wins)}/{len(closed)})')
print(f'Total P&L: ${total_pnl:.2f}')
print(f'Avg Win: ${avg_win:.2f}')
print(f'Avg Loss: ${avg_loss:.2f}')
print(f'Risk/Reward Ratio: {abs(avg_win/avg_loss):.2f}:1' if avg_loss != 0 else 'N/A')
print()

# Analyze by duration
durations = []
for t in closed:
    if t.get('entry_time') and t.get('exit_time'):
        entry = datetime.fromisoformat(t['entry_time'])
        exit = datetime.fromisoformat(t['exit_time'])
        dur_min = (exit - entry).total_seconds() / 60
        durations.append((dur_min, t.get('pnl', 0)))

if durations:
    avg_duration = sum(d[0] for d in durations) / len(durations)
    print(f'Avg Hold Time: {avg_duration:.1f} minutes')
    print()

# Last 50 trades analysis
last_50 = closed[-50:] if len(closed) >= 50 else closed
wins_50 = [t for t in last_50 if t.get('pnl', 0) > 0]
losses_50 = [t for t in last_50 if t.get('pnl', 0) < 0]
pnl_50 = sum(t.get('pnl', 0) for t in last_50)

print(f'LAST 50 TRADES:')
print(f'  Win Rate: {len(wins_50)/len(last_50)*100:.1f}% ({len(wins_50)}/{len(last_50)})')
print(f'  P&L: ${pnl_50:.2f}')
if wins_50:
    avg_win_50 = sum(t.get("pnl", 0) for t in wins_50)/len(wins_50)
    print(f'  Avg Win: ${avg_win_50:.2f}')
if losses_50:
    avg_loss_50 = sum(t.get("pnl", 0) for t in losses_50)/len(losses_50)
    print(f'  Avg Loss: ${avg_loss_50:.2f}')
    if wins_50:
        print(f'  Risk/Reward: {abs(avg_win_50/avg_loss_50):.2f}:1')
print()

# Analyze win/loss sizes
print('WIN SIZE DISTRIBUTION:')
tiny_wins = [t for t in wins if 0 < t.get('pnl', 0) < 0.10]
small_wins = [t for t in wins if 0.10 <= t.get('pnl', 0) < 0.30]
medium_wins = [t for t in wins if 0.30 <= t.get('pnl', 0) < 0.50]
large_wins = [t for t in wins if t.get('pnl', 0) >= 0.50]

print(f'  <$0.10 (tiny): {len(tiny_wins)} trades ({len(tiny_wins)/len(wins)*100:.1f}%), ${sum(t.get("pnl", 0) for t in tiny_wins):.2f} total')
print(f'  $0.10-0.30: {len(small_wins)} trades ({len(small_wins)/len(wins)*100:.1f}%), ${sum(t.get("pnl", 0) for t in small_wins):.2f} total')
print(f'  $0.30-0.50: {len(medium_wins)} trades ({len(medium_wins)/len(wins)*100:.1f}%), ${sum(t.get("pnl", 0) for t in medium_wins):.2f} total')
print(f'  $0.50+: {len(large_wins)} trades ({len(large_wins)/len(wins)*100:.1f}%), ${sum(t.get("pnl", 0) for t in large_wins):.2f} total')
print()

print('LOSS SIZE DISTRIBUTION:')
tiny_losses = [t for t in losses if -0.10 < t.get('pnl', 0) < 0]
small_losses = [t for t in losses if -0.30 <= t.get('pnl', 0) < -0.10]
medium_losses = [t for t in losses if -0.50 <= t.get('pnl', 0) < -0.30]
large_losses = [t for t in losses if t.get('pnl', 0) < -0.50]

print(f'  >-$0.10 (tiny): {len(tiny_losses)} trades ({len(tiny_losses)/len(losses)*100:.1f}%), ${sum(t.get("pnl", 0) for t in tiny_losses):.2f} total')
print(f'  -$0.10 to -$0.30: {len(small_losses)} trades ({len(small_losses)/len(losses)*100:.1f}%), ${sum(t.get("pnl", 0) for t in small_losses):.2f} total')
print(f'  -$0.30 to -$0.50: {len(medium_losses)} trades ({len(medium_losses)/len(losses)*100:.1f}%), ${sum(t.get("pnl", 0) for t in medium_losses):.2f} total')
print(f'  <-$0.50 (large): {len(large_losses)} trades ({len(large_losses)/len(losses)*100:.1f}%), ${sum(t.get("pnl", 0) for t in large_losses):.2f} total')
print()

# Analyze best vs worst trades
print('BEST 10 TRADES:')
best = sorted(closed, key=lambda t: t.get('pnl', 0), reverse=True)[:10]
for i, t in enumerate(best, 1):
    print(f'  {i}. {t["symbol"]}: ${t.get("pnl", 0):.2f}')
print()

print('WORST 10 TRADES:')
worst = sorted(closed, key=lambda t: t.get('pnl', 0))[:10]
for i, t in enumerate(worst, 1):
    print(f'  {i}. {t["symbol"]}: ${t.get("pnl", 0):.2f}')
print()

# Calculate what would happen if we cut losses better
print('WHAT IF ANALYSIS:')
big_losses = [t for t in losses if t.get('pnl', 0) < -0.20]
big_loss_total = sum(t.get('pnl', 0) for t in big_losses)
print(f'  Big losses (>$0.20): {len(big_losses)} trades, ${big_loss_total:.2f} total')
print(f'  If stopped at -$0.20: Would save ${abs(big_loss_total) - (len(big_losses) * 0.20):.2f}')
print(f'  New P&L would be: ${total_pnl + (abs(big_loss_total) - (len(big_losses) * 0.20)):.2f}')
