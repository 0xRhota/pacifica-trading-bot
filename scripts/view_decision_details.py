#!/usr/bin/env python3
"""
View Detailed LLM Bot Decision Breakdown
Shows complete decision-making process for each cycle
"""
import re
import sys

def extract_decision_cycle(lines, start_idx):
    """Extract complete decision cycle starting from given index"""
    cycle = {
        'timestamp': '',
        'positions': '?',
        'market_data': [],
        'deep42_query': '',
        'tokens_selected': [],
        'token_analyses': [],
        'position_evaluations': [],
        'decision_action': '',
        'decision_symbol': '',
        'decision_reason': '',
        'decision_cost': '',
        'execution_result': '',
        'filled': ''
    }

    # Get timestamp
    timestamp_match = re.search(r'Decision Cycle - ([\d\-: ]+)', lines[start_idx])
    cycle['timestamp'] = timestamp_match.group(1) if timestamp_match else "Unknown"

    # Search through next ~500 lines for all cycle data
    end_idx = min(start_idx + 500, len(lines))

    # Extract market data table
    in_market_data = False
    found_table_header = False
    for i in range(start_idx, end_idx):
        line = lines[i]

        # Market data table extraction - look for "Market Data (Latest):"
        if "Market Data (Latest):" in line:
            in_market_data = True
            continue

        if in_market_data:
            # Stop at LLM decision section or when we hit the separator bar
            if "Getting trading decision from LLM" in line or "LLM DECISION:" in line:
                in_market_data = False
                continue

            # Extract the content after "INFO -   "
            if "INFO -   " in line:
                # Get everything after the "INFO -   " prefix
                content = line.split("INFO -   ", 1)[1] if "INFO -   " in line else ""
                stripped = content.strip()

                # Skip empty lines
                if not stripped:
                    continue

                # Skip the Sources line
                if stripped.startswith("Sources:"):
                    continue

                # Look for the header row
                if "Symbol" in stripped and "Price" in stripped and "Funding" in stripped:
                    found_table_header = True
                    cycle['market_data'].append(stripped)
                    continue

                # After finding header, get separator and data rows
                if found_table_header:
                    # If it's a separator or data row, include it
                    if "-" * 10 in stripped or "$" in stripped or any(token in stripped.split()[0:1] for token in ["ETH", "BTC", "SOL", "PUMP", "XRP", "DOGE", "HYPE", "FARTCOIN"]):
                        cycle['market_data'].append(stripped)
                    # Stop when we hit the end separator
                    if stripped.startswith("===="):
                        in_market_data = False
                        break

    # Now parse other fields
    for i in range(start_idx, end_idx):
        line = lines[i]

        # Open positions
        if "Open positions:" in line:
            pos_match = re.search(r'Open positions: (\d+)', line)
            if pos_match:
                cycle['positions'] = pos_match.group(1)

        # Deep42 query
        if "Generated Deep42 query:" in line:
            query_match = re.search(r'Generated Deep42 query: (.+)', line)
            if query_match:
                cycle['deep42_query'] = query_match.group(1).strip()

        # Tokens selected
        if "LLM selected tokens:" in line:
            tokens_match = re.search(r"LLM selected tokens: \[([^\]]+)\]", line)
            if tokens_match:
                tokens_str = tokens_match.group(1)
                cycle['tokens_selected'] = [t.strip().strip("'\"") for t in tokens_str.split(',')]

        # Token analyses
        if "Deep42 token analysis:" in line:
            token_match = re.search(r'Deep42 token analysis: (\w+)', line)
            if token_match:
                cycle['token_analyses'].append(token_match.group(1))

        # Position evaluations
        if "Deep42 position evaluation:" in line:
            pos_match = re.search(r'Deep42 position evaluation: (.+)', line)
            if pos_match:
                cycle['position_evaluations'].append(pos_match.group(1))

        # Decision
        if "LLM DECISION:" in line:
            # Action
            if i+1 < len(lines):
                action_match = re.search(r'Action: (\w+)', lines[i+1])
                if action_match:
                    cycle['decision_action'] = action_match.group(1)

            # Find Symbol and Reason dynamically (Symbol may not exist for NOTHING)
            for offset in range(2, min(8, len(lines)-i)):
                check_line = lines[i+offset]

                # Symbol
                if "Symbol:" in check_line and not cycle['decision_symbol']:
                    symbol_match = re.search(r'Symbol: (.+)', check_line)
                    if symbol_match:
                        cycle['decision_symbol'] = symbol_match.group(1).strip()

                # Reason
                if "Reason:" in check_line and not cycle['decision_reason']:
                    full_line = check_line
                    reason_match = re.search(r'Reason: (.+)', full_line)
                    if reason_match:
                        cycle['decision_reason'] = reason_match.group(1).strip()

                # Cost
                if "Cost:" in check_line and not cycle['decision_cost']:
                    cost_match = re.search(r'Cost: \$([\d.]+)', check_line)
                    if cost_match:
                        cycle['decision_cost'] = cost_match.group(1)
                    break  # Cost is always last

        # Execution result
        if "Execution successful" in line or "Execution failed" in line:
            cycle['execution_result'] = "✅ SUCCESS" if "successful" in line else "❌ FAILED"

        if "Filled:" in line:
            filled_match = re.search(r'Filled: ([\d.]+) @ \$([\d.]+)', line)
            if filled_match:
                cycle['filled'] = filled_match.group(0)

        # Stop at next decision cycle
        if i > start_idx and "Decision Cycle -" in line:
            break

    return cycle

def format_cycle(cycle, index):
    """Format a complete decision cycle"""
    print(f"\n\n{'█'*100}")
    print(f"█  CYCLE #{index} - {cycle['timestamp']}")
    print(f"{'█'*100}\n")

    print(f"📊 Open Positions: {cycle['positions']}")

    if cycle['deep42_query']:
        print(f"\n🔍 Deep42 Query: {cycle['deep42_query']}")

    if cycle['tokens_selected']:
        print(f"\n🎯 Token Analysis: {len(cycle['token_analyses'])} tokens analyzed ({', '.join(cycle['tokens_selected'])})")

    # Show market data count
    if cycle['market_data']:
        # Count actual data rows (skip header and separator)
        data_rows = [r for r in cycle['market_data'] if '$' in r]
        print(f"\n📈 Market Data: {len(data_rows)} tokens tracked")

        # If action was taken, show that symbol's data
        if cycle['decision_symbol']:
            print(f"\n   {cycle['decision_symbol']} Data:")
            for row in cycle['market_data']:
                if row.startswith(cycle['decision_symbol'] + ' '):
                    print(f"   {row}")
                    break

    print(f"\n{'─'*100}")
    print(f"⚡ DECISION")
    print(f"{'─'*100}")
    print(f"Action:  {cycle['decision_action']}{' ' + cycle['decision_symbol'] if cycle['decision_symbol'] else ''}")
    print(f"Reason:  {cycle['decision_reason']}")
    print(f"Cost:    ${cycle['decision_cost']}")

    if cycle['execution_result']:
        print(f"\nExecution: {cycle['execution_result']}")
        if cycle['filled']:
            print(f"           {cycle['filled']}")

def main():
    log_file = 'logs/llm_bot.log'

    print("\n" + "="*100)
    print("LLM BOT - DETAILED DECISION BREAKDOWN")
    print("="*100)

    with open(log_file, 'r') as f:
        lines = f.readlines()

    # Find all decision cycles
    cycle_indices = []
    for i, line in enumerate(lines):
        if "Decision Cycle -" in line:
            cycle_indices.append(i)

    if not cycle_indices:
        print("\nNo decision cycles found in log file.")
        return

    print(f"\nTotal Cycles Found: {len(cycle_indices)}")

    # Extract and display each cycle
    for idx, start_idx in enumerate(cycle_indices, 1):
        cycle = extract_decision_cycle(lines, start_idx)
        format_cycle(cycle, idx)

    print(f"\n{'='*100}")
    print(f"END OF DECISIONS (Total: {len(cycle_indices)})")
    print(f"{'='*100}\n")

if __name__ == "__main__":
    main()
