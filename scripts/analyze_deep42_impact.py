import json
import re

# Read V2 trades
with open('logs/trades/lighter.json', 'r') as f:
    trades = json.load(f)

closed = [t for t in trades if t.get('status') == 'closed']

print('=== ANALYZING DEEP42 IMPACT ON EXITS ===\n')

# Find exits mentioning "risk-off" or "Deep42" or "fear"
risk_off_exits = []
other_exits = []

for t in closed:
    reason = t.get('exit_reason', '').lower()
    if 'risk-off' in reason or 'risk off' in reason or 'fear' in reason or 'deep42' in reason:
        risk_off_exits.append(t)
    else:
        other_exits.append(t)

print(f'Exits mentioning risk-off/fear: {len(risk_off_exits)} ({len(risk_off_exits)/len(closed)*100:.1f}%)')
print(f'Exits for other reasons: {len(other_exits)} ({len(other_exits)/len(closed)*100:.1f}%)')
print()

# Analyze P&L of risk-off exits vs others
if risk_off_exits:
    risk_off_pnl = sum(t.get('pnl', 0) for t in risk_off_exits)
    risk_off_avg = risk_off_pnl / len(risk_off_exits)
    print(f'Risk-off exits: ${risk_off_pnl:.4f} total, ${risk_off_avg:.4f} avg')

    # How many were winners?
    risk_off_wins = [t for t in risk_off_exits if t.get('pnl', 0) > 0]
    print(f'  {len(risk_off_wins)} wins, {len(risk_off_exits) - len(risk_off_wins)} losses')

    # What was avg profit % when closed?
    risk_off_pct = [t.get('pnl_pct', 0) * 100 for t in risk_off_exits if t.get('pnl_pct')]
    if risk_off_pct:
        avg_exit_pct = sum(risk_off_pct) / len(risk_off_pct)
        print(f'  Avg exit at {avg_exit_pct:.2f}% profit/loss')
    print()

if other_exits:
    other_pnl = sum(t.get('pnl', 0) for t in other_exits)
    other_avg = other_pnl / len(other_exits)
    print(f'Other exits: ${other_pnl:.4f} total, ${other_avg:.4f} avg')
    print()

# Show examples of premature exits due to risk-off
print('PREMATURE "RISK-OFF" EXITS (closed with profit <1%):')
premature = [t for t in risk_off_exits if 0 < t.get('pnl_pct', 0) * 100 < 1]
premature.sort(key=lambda t: t.get('pnl_pct', 0), reverse=True)

for i, t in enumerate(premature[:10], 1):
    pct = t.get('pnl_pct', 0) * 100
    reason = t.get('exit_reason', '').replace('"', '')[:100]
    print(f'{i}. {t["symbol"]}: +{pct:.2f}% - "{reason}..."')
print()

# Calculate lost profit
print('LOST PROFIT ANALYSIS:')
print('If these positions hit 2% target instead:')
total_actual = sum(t.get('pnl', 0) for t in premature)
# Estimate: if they hit 2% instead of their tiny profit
avg_position_size = sum(t.get('size', 0) * t.get('entry_price', 0) for t in premature) / len(premature) if premature else 0
potential_at_2pct = avg_position_size * 0.02 * len(premature)
print(f'  Actual P&L: ${total_actual:.2f}')
print(f'  Potential at 2%: ${potential_at_2pct:.2f}')
print(f'  Lost opportunity: ${potential_at_2pct - total_actual:.2f}')
print()

# Analyze entries
print('=== DEEP42 IMPACT ON ENTRIES ===\n')
# Check entry notes mentioning Deep42
entries_with_deep42 = [t for t in closed if 'deep42' in t.get('notes', '').lower() or 'quality' in t.get('notes', '').lower()]
print(f'Entries mentioning Deep42/quality: {len(entries_with_deep42)} ({len(entries_with_deep42)/len(closed)*100:.1f}%)')

# Were those trades better or worse?
if entries_with_deep42:
    deep42_pnl = sum(t.get('pnl', 0) for t in entries_with_deep42)
    deep42_avg = deep42_pnl / len(entries_with_deep42)
    print(f'  Total P&L: ${deep42_pnl:.4f}, Avg: ${deep42_avg:.4f}')

    deep42_wins = [t for t in entries_with_deep42 if t.get('pnl', 0) > 0]
    deep42_wr = len(deep42_wins) / len(entries_with_deep42) * 100
    print(f'  Win Rate: {deep42_wr:.1f}%')
print()

print('=== CONCLUSION ===')
print()
print('Deep42 appears to cause:')
print(f'1. {len(risk_off_exits)} exits ({len(risk_off_exits)/len(closed)*100:.1f}%) due to "risk-off" fear')
print(f'2. Avg exit at +{avg_exit_pct:.2f}% instead of 2% target')
print(f'3. Estimated ${potential_at_2pct - total_actual:.2f} in lost profit')
print()
print('Pure technicals would:')
print('✅ Remove "risk-off regime" panic')
print('✅ Let winners run based on technical signals only')
print('✅ More objective decision-making')
print()
print('But we would LOSE:')
print('❌ Pump-and-dump detection (quality scores <5)')
print('❌ BTC health correlation')
print('❌ Macro regime awareness')
