#!/usr/bin/env python3
"""
View LLM Bot Decisions
Extracts and formats all trading decisions from bot logs
"""
import re
import sys
from datetime import datetime

def parse_decisions(log_file):
    """Parse all decisions from log file"""
    with open(log_file, 'r') as f:
        lines = f.readlines()

    decisions = []
    i = 0
    while i < len(lines):
        # Look for decision cycle start
        if "Decision Cycle -" in lines[i]:
            timestamp_match = re.search(r'Decision Cycle - ([\d\-: ]+)', lines[i])
            timestamp = timestamp_match.group(1) if timestamp_match else "Unknown"

            # Find positions
            positions = "?"
            for j in range(i, min(i+20, len(lines))):
                if "Open positions:" in lines[j]:
                    pos_match = re.search(r'Open positions: (\d+)', lines[j])
                    if pos_match:
                        positions = pos_match.group(1)
                    break

            # Find LLM DECISION
            for j in range(i, min(i+300, len(lines))):
                if "LLM DECISION:" in lines[j]:
                    # Extract action (next line)
                    action_match = re.search(r'Action: (\w+)', lines[j+1]) if j+1 < len(lines) else None
                    action = action_match.group(1) if action_match else "UNKNOWN"

                    # Extract symbol (if present)
                    symbol = "N/A"
                    if j+2 < len(lines) and "Symbol:" in lines[j+2]:
                        symbol_match = re.search(r'Symbol: (.+)', lines[j+2])
                        symbol = symbol_match.group(1).strip() if symbol_match else "N/A"

                    # Extract reason
                    reason = ""
                    if "Reason:" in lines[j+3]:
                        reason_match = re.search(r'Reason: (.+)', lines[j+3])
                        reason = reason_match.group(1).strip() if reason_match else ""
                        # Handle multi-line reasons
                        k = j + 4
                        while k < len(lines) and "Cost:" not in lines[k] and "====" not in lines[k]:
                            reason += " " + lines[k].strip().split("INFO - ")[-1]
                            k += 1
                        if len(reason) > 300:
                            reason = reason[:297] + "..."

                    # Extract cost
                    cost = "?"
                    for k in range(j, min(j+10, len(lines))):
                        if "Cost:" in lines[k]:
                            cost_match = re.search(r'Cost: \$([\d.]+)', lines[k])
                            cost = cost_match.group(1) if cost_match else "?"
                            break

                    # Look for execution result
                    execution = "N/A"
                    filled = "N/A"
                    for k in range(j, min(j+20, len(lines))):
                        if "Execution successful" in lines[k] or "Execution failed" in lines[k]:
                            execution = "✅ SUCCESS" if "successful" in lines[k] else "❌ FAILED"
                        if "Filled:" in lines[k]:
                            filled_match = re.search(r'Filled: ([\d.]+) @ \$([\d.]+)', lines[k])
                            filled = filled_match.group(0) if filled_match else "N/A"
                            break

                    decision = {
                        'timestamp': timestamp,
                        'action': action,
                        'symbol': symbol,
                        'reason': reason,
                        'cost': cost,
                        'positions': positions,
                        'execution': execution,
                        'filled': filled
                    }
                    decisions.append(decision)
                    break

        i += 1

    return decisions

def format_decision(d, index):
    """Format a single decision for display"""
    symbol_display = f"{d['symbol']}" if d['symbol'] != "N/A" else ""

    print(f"\n{'='*80}")
    print(f"Decision #{index} - {d['timestamp']}")
    print(f"{'='*80}")
    print(f"Action:    {d['action']} {symbol_display}")
    print(f"Positions: {d['positions']} open")
    print(f"Reason:    {d['reason']}")
    print(f"Cost:      ${d['cost']}")
    print(f"Result:    {d['execution']}")
    if d['filled'] != "N/A":
        print(f"           {d['filled']}")

def main():
    log_file = 'logs/llm_bot.log'

    print("\n" + "="*80)
    print("LLM BOT TRADING DECISIONS")
    print("="*80)

    decisions = parse_decisions(log_file)

    if not decisions:
        print("\nNo decisions found in log file.")
        return

    print(f"\nTotal Decisions: {len(decisions)}")
    print(f"Log File: {log_file}")

    # Show summary stats
    actions = {}
    for d in decisions:
        actions[d['action']] = actions.get(d['action'], 0) + 1

    print(f"\nAction Breakdown:")
    for action, count in sorted(actions.items()):
        print(f"  {action}: {count}")

    # Show all decisions
    for i, decision in enumerate(decisions, 1):
        format_decision(decision, i)

    print(f"\n{'='*80}")
    print(f"End of Decisions (Total: {len(decisions)})")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
