#!/usr/bin/env python3
"""
Analyze winning wallet trade history from Pacifica to identify successful patterns.

Usage:
    python analyze_wallet_trades.py pacifica-trade-history-9R1cvSEd-2025-11-07.csv
"""

import pandas as pd
import sys
from datetime import datetime
from pathlib import Path


def parse_currency(value):
    """Convert currency strings like '$1,234.56' to float."""
    if pd.isna(value) or value == '':
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    # Remove $ and commas
    cleaned = str(value).replace('$', '').replace(',', '')
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def load_and_clean_data(csv_path):
    """Load CSV and clean data types."""
    df = pd.read_csv(csv_path)

    # Parse currency columns
    df['Trade Value'] = df['Trade Value'].apply(parse_currency)
    df['Fee'] = df['Fee'].apply(parse_currency)
    df['Realized PnL'] = df['Realized PnL'].apply(parse_currency)

    # Parse timestamps
    df['Time'] = pd.to_datetime(df['Time'])

    # Parse numeric columns
    df['Size'] = pd.to_numeric(df['Size'], errors='coerce')
    df['Price'] = pd.to_numeric(df['Price'], errors='coerce')

    return df


def match_open_close_trades(df):
    """
    Match "Open Long/Short" entries with their corresponding "Close Long/Short".
    CSV Side column has values: "Open Long", "Open Short", "Close Long", "Close Short"

    Returns list of completed round-trip trades.
    """
    trades = []

    # Group by symbol
    for symbol in df['Symbol'].unique():
        symbol_df = df[df['Symbol'] == symbol].sort_values('Time').reset_index(drop=True)

        # Track open positions (FIFO)
        open_longs = []
        open_shorts = []

        for _, row in symbol_df.iterrows():
            side = row['Side']
            size = row['Size']
            price = row['Price']
            fee = row['Fee']
            trade_value = row['Trade Value']
            time = row['Time']

            if side == 'Open Long':
                # Opening new long position
                open_longs.append({
                    'time': time,
                    'price': price,
                    'size': size,
                    'fee': fee,
                    'trade_value': trade_value
                })

            elif side == 'Close Long' and open_longs:
                # Closing long position (FIFO)
                entry = open_longs.pop(0)

                hold_time_seconds = (time - entry['time']).total_seconds()
                hold_time_minutes = hold_time_seconds / 60

                # Calculate P&L
                entry_cost = entry['trade_value'] + entry['fee']
                exit_value = trade_value - fee
                pnl = exit_value - entry_cost
                pnl_pct = (pnl / entry_cost) * 100 if entry_cost > 0 else 0

                trades.append({
                    'symbol': symbol,
                    'side': 'LONG',
                    'entry_time': entry['time'],
                    'exit_time': time,
                    'hold_time_minutes': hold_time_minutes,
                    'entry_price': entry['price'],
                    'exit_price': price,
                    'size': entry['size'],
                    'entry_cost': entry_cost,
                    'exit_value': exit_value,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'total_fees': entry['fee'] + fee
                })

            elif side == 'Open Short':
                # Opening new short position
                open_shorts.append({
                    'time': time,
                    'price': price,
                    'size': size,
                    'fee': fee,
                    'trade_value': trade_value
                })

            elif side == 'Close Short' and open_shorts:
                # Closing short position (FIFO)
                entry = open_shorts.pop(0)

                hold_time_seconds = (time - entry['time']).total_seconds()
                hold_time_minutes = hold_time_seconds / 60

                # For shorts: profit when exit price < entry price
                entry_value = entry['trade_value'] - entry['fee']
                exit_cost = trade_value + fee
                pnl = entry_value - exit_cost
                pnl_pct = (pnl / entry_value) * 100 if entry_value > 0 else 0

                trades.append({
                    'symbol': symbol,
                    'side': 'SHORT',
                    'entry_time': entry['time'],
                    'exit_time': time,
                    'hold_time_minutes': hold_time_minutes,
                    'entry_price': entry['price'],
                    'exit_price': price,
                    'size': entry['size'],
                    'entry_cost': entry_value,
                    'exit_value': exit_cost,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'total_fees': entry['fee'] + fee
                })

    return pd.DataFrame(trades)


def analyze_trades(trades_df):
    """Generate comprehensive analysis of trading patterns."""

    if len(trades_df) == 0:
        return "No completed trades found in dataset."

    # Basic stats
    total_trades = len(trades_df)
    winning_trades = trades_df[trades_df['pnl'] > 0]
    losing_trades = trades_df[trades_df['pnl'] < 0]

    win_rate = (len(winning_trades) / total_trades) * 100

    avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
    avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0

    avg_win_pct = winning_trades['pnl_pct'].mean() if len(winning_trades) > 0 else 0
    avg_loss_pct = losing_trades['pnl_pct'].mean() if len(losing_trades) > 0 else 0

    total_pnl = trades_df['pnl'].sum()
    total_fees = trades_df['total_fees'].sum()

    avg_hold_time = trades_df['hold_time_minutes'].mean()
    median_hold_time = trades_df['hold_time_minutes'].median()

    # Hold time categories
    scalp_trades = trades_df[trades_df['hold_time_minutes'] <= 15]
    short_swing = trades_df[(trades_df['hold_time_minutes'] > 15) & (trades_df['hold_time_minutes'] <= 60)]
    medium_swing = trades_df[(trades_df['hold_time_minutes'] > 60) & (trades_df['hold_time_minutes'] <= 240)]
    long_swing = trades_df[trades_df['hold_time_minutes'] > 240]

    # Position sizing
    avg_position_size = trades_df['entry_cost'].mean()
    median_position_size = trades_df['entry_cost'].median()

    # Build report
    report = []
    report.append("=" * 80)
    report.append("WINNING WALLET ANALYSIS - PACIFICA")
    report.append("=" * 80)
    report.append("")

    report.append("📊 OVERALL PERFORMANCE")
    report.append("-" * 80)
    report.append(f"Total Trades: {total_trades}")
    report.append(f"Win Rate: {win_rate:.1f}%")
    report.append(f"Total P&L: ${total_pnl:.2f}")
    report.append(f"Total Fees: ${total_fees:.2f}")
    report.append(f"Net P&L (after fees): ${total_pnl - total_fees:.2f}")
    report.append("")

    report.append("💰 WIN/LOSS BREAKDOWN")
    report.append("-" * 80)
    report.append(f"Winning Trades: {len(winning_trades)} (${avg_win:.2f} avg, {avg_win_pct:.2f}% avg)")
    report.append(f"Losing Trades: {len(losing_trades)} (${avg_loss:.2f} avg, {avg_loss_pct:.2f}% avg)")

    if avg_loss != 0:
        profit_factor = abs(avg_win / avg_loss)
        report.append(f"Profit Factor (avg win / avg loss): {profit_factor:.2f}x")
    report.append("")

    report.append("⏱️  HOLD TIME ANALYSIS")
    report.append("-" * 80)
    report.append(f"Average Hold Time: {avg_hold_time:.1f} minutes ({avg_hold_time/60:.1f} hours)")
    report.append(f"Median Hold Time: {median_hold_time:.1f} minutes ({median_hold_time/60:.1f} hours)")
    report.append("")
    report.append(f"Scalp (≤15 min): {len(scalp_trades)} trades ({len(scalp_trades)/total_trades*100:.1f}%)")
    report.append(f"Short Swing (15-60 min): {len(short_swing)} trades ({len(short_swing)/total_trades*100:.1f}%)")
    report.append(f"Medium Swing (1-4 hrs): {len(medium_swing)} trades ({len(medium_swing)/total_trades*100:.1f}%)")
    report.append(f"Long Swing (>4 hrs): {len(long_swing)} trades ({len(long_swing)/total_trades*100:.1f}%)")
    report.append("")

    # Win rate by hold time category
    report.append("Win Rate by Hold Time:")
    if len(scalp_trades) > 0:
        scalp_win_rate = (len(scalp_trades[scalp_trades['pnl'] > 0]) / len(scalp_trades)) * 100
        report.append(f"  Scalp: {scalp_win_rate:.1f}%")
    if len(short_swing) > 0:
        short_win_rate = (len(short_swing[short_swing['pnl'] > 0]) / len(short_swing)) * 100
        report.append(f"  Short Swing: {short_win_rate:.1f}%")
    if len(medium_swing) > 0:
        medium_win_rate = (len(medium_swing[medium_swing['pnl'] > 0]) / len(medium_swing)) * 100
        report.append(f"  Medium Swing: {medium_win_rate:.1f}%")
    if len(long_swing) > 0:
        long_win_rate = (len(long_swing[long_swing['pnl'] > 0]) / len(long_swing)) * 100
        report.append(f"  Long Swing: {long_win_rate:.1f}%")
    report.append("")

    report.append("💵 POSITION SIZING")
    report.append("-" * 80)
    report.append(f"Average Position Size: ${avg_position_size:.2f}")
    report.append(f"Median Position Size: ${median_position_size:.2f}")
    report.append(f"Position Size Range: ${trades_df['entry_cost'].min():.2f} - ${trades_df['entry_cost'].max():.2f}")
    report.append("")

    report.append("🎯 SYMBOL BREAKDOWN")
    report.append("-" * 80)
    for symbol in trades_df['symbol'].unique():
        sym_trades = trades_df[trades_df['symbol'] == symbol]
        sym_wins = sym_trades[sym_trades['pnl'] > 0]
        sym_win_rate = (len(sym_wins) / len(sym_trades)) * 100
        sym_pnl = sym_trades['pnl'].sum()
        report.append(f"{symbol}: {len(sym_trades)} trades, {sym_win_rate:.1f}% win rate, ${sym_pnl:.2f} P&L")
    report.append("")

    report.append("🔑 KEY INSIGHTS FOR PACIFICA STRATEGY")
    report.append("-" * 80)

    # Generate insights
    insights = []

    if median_hold_time > 60:
        insights.append(f"✅ Longer holds (median {median_hold_time/60:.1f} hrs) suggest swing trading works better with fees")
    else:
        insights.append(f"⚠️  Shorter holds (median {median_hold_time:.1f} min) - fees may eat profits")

    if win_rate >= 60:
        insights.append(f"✅ High win rate ({win_rate:.1f}%) - consistent small wins strategy")
    elif win_rate >= 50:
        insights.append(f"✅ Balanced win rate ({win_rate:.1f}%) with good profit factor")
    else:
        insights.append(f"⚠️  Lower win rate ({win_rate:.1f}%) - relies on large winners")

    if avg_position_size > 100:
        insights.append(f"✅ Larger positions (${avg_position_size:.0f} avg) help offset fee impact")
    else:
        insights.append(f"⚠️  Small positions (${avg_position_size:.0f} avg) - fees are higher % of P&L")

    fee_pct_of_pnl = (total_fees / abs(total_pnl)) * 100 if total_pnl != 0 else 0
    insights.append(f"💰 Fees represent {fee_pct_of_pnl:.1f}% of gross P&L")

    for insight in insights:
        report.append(insight)

    report.append("")
    report.append("=" * 80)

    return "\n".join(report)


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_wallet_trades.py <csv_file>")
        sys.exit(1)

    csv_path = sys.argv[1]

    if not Path(csv_path).exists():
        print(f"Error: File not found: {csv_path}")
        sys.exit(1)

    print("Loading and cleaning data...")
    df = load_and_clean_data(csv_path)
    print(f"Loaded {len(df)} raw trade entries")

    print("Matching open/close trades...")
    trades_df = match_open_close_trades(df)
    print(f"Matched {len(trades_df)} completed trades")

    # Save matched trades to CSV
    output_csv = csv_path.replace('.csv', '_matched_trades.csv')
    trades_df.to_csv(output_csv, index=False)
    print(f"Saved matched trades to: {output_csv}")

    # Generate and print analysis
    print("\n")
    analysis = analyze_trades(trades_df)
    print(analysis)

    # Save analysis to markdown
    output_md = csv_path.replace('.csv', '_analysis.md')
    with open(output_md, 'w') as f:
        f.write(analysis)
    print(f"\nAnalysis saved to: {output_md}")


if __name__ == '__main__':
    main()
