#!/usr/bin/env python3
"""
Comprehensive trade analysis script.
Analyzes all trade JSON files and generates performance metrics.
"""

import json
import os
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import re

# Define paths
TRADES_DIR = Path("/Users/admin/Documents/Projects/pacifica-trading-bot/logs/trades")
ARCHIVE_DIR = TRADES_DIR / "archive"


def parse_strategy_from_filename(filename: str) -> tuple[str, str]:
    """Extract exchange and strategy name from filename."""
    # Pattern: {exchange}_{strategy}_{date}.json or {exchange}.json
    name = filename.replace(".json", "")

    # Check for archive pattern: lighter_deep42-v1_20251113_112324
    parts = name.split("_")

    if len(parts) >= 2:
        exchange = parts[0]
        # Check if second part looks like a date (8 digits)
        if len(parts) > 1 and parts[1].isdigit() and len(parts[1]) == 8:
            strategy = "default"
        elif len(parts) > 1 and not parts[1].isdigit():
            # Has strategy name
            strategy = parts[1]
        else:
            strategy = "default"
    else:
        exchange = name
        strategy = "default"

    return exchange, strategy


def analyze_trades(trades: list, exchange: str, strategy: str, filename: str) -> dict:
    """Analyze a list of trades and return metrics."""
    if not trades:
        return None

    # Filter closed trades only
    closed_trades = [t for t in trades if t.get("status") == "closed" and t.get("pnl") is not None]

    if not closed_trades:
        return None

    # Basic metrics
    total_trades = len(closed_trades)
    wins = [t for t in closed_trades if t.get("pnl", 0) > 0]
    losses = [t for t in closed_trades if t.get("pnl", 0) < 0]
    breakeven = [t for t in closed_trades if t.get("pnl", 0) == 0]

    win_count = len(wins)
    loss_count = len(losses)
    breakeven_count = len(breakeven)

    win_rate = win_count / total_trades if total_trades > 0 else 0

    total_pnl = sum(t.get("pnl", 0) for t in closed_trades)

    avg_win = sum(t.get("pnl", 0) for t in wins) / win_count if win_count > 0 else 0
    avg_loss = sum(t.get("pnl", 0) for t in losses) / loss_count if loss_count > 0 else 0

    # Symbol breakdown
    symbols = defaultdict(lambda: {"trades": 0, "wins": 0, "losses": 0, "pnl": 0})
    for t in closed_trades:
        symbol = t.get("symbol", "UNKNOWN")
        symbols[symbol]["trades"] += 1
        symbols[symbol]["pnl"] += t.get("pnl", 0)
        if t.get("pnl", 0) > 0:
            symbols[symbol]["wins"] += 1
        elif t.get("pnl", 0) < 0:
            symbols[symbol]["losses"] += 1

    # Direction breakdown
    direction_stats = {
        "LONG": {"wins": 0, "losses": 0, "pnl": 0, "trades": 0},
        "SHORT": {"wins": 0, "losses": 0, "pnl": 0, "trades": 0}
    }

    for t in closed_trades:
        side = t.get("side", "").upper()
        if side in ["LONG", "BUY"]:
            direction = "LONG"
        elif side in ["SHORT", "SELL"]:
            direction = "SHORT"
        else:
            continue

        direction_stats[direction]["trades"] += 1
        direction_stats[direction]["pnl"] += t.get("pnl", 0)
        if t.get("pnl", 0) > 0:
            direction_stats[direction]["wins"] += 1
        elif t.get("pnl", 0) < 0:
            direction_stats[direction]["losses"] += 1

    # Confidence calibration
    confidence_buckets = defaultdict(lambda: {"total": 0, "wins": 0})
    has_confidence = False

    for t in closed_trades:
        conf = t.get("confidence")
        if conf is not None:
            has_confidence = True
            # Bucket by 0.1 intervals
            bucket = round(conf, 1)
            confidence_buckets[bucket]["total"] += 1
            if t.get("pnl", 0) > 0:
                confidence_buckets[bucket]["wins"] += 1

    confidence_calibration = {}
    if has_confidence:
        for bucket, data in sorted(confidence_buckets.items()):
            actual_accuracy = data["wins"] / data["total"] if data["total"] > 0 else 0
            confidence_calibration[str(bucket)] = {
                "expected": bucket,
                "actual": round(actual_accuracy, 4),
                "count": data["total"]
            }

    # Date range
    timestamps = []
    for t in closed_trades:
        ts = t.get("timestamp") or t.get("entry_timestamp")
        if ts:
            timestamps.append(ts)

    first_trade = min(timestamps) if timestamps else None
    last_trade = max(timestamps) if timestamps else None

    # Hold time distribution (if entry/exit times present)
    hold_times = []
    for t in closed_trades:
        entry_ts = t.get("timestamp") or t.get("entry_timestamp")
        exit_ts = t.get("exit_timestamp")
        if entry_ts and exit_ts:
            try:
                if isinstance(entry_ts, str):
                    entry_dt = datetime.fromisoformat(entry_ts.replace("Z", "+00:00"))
                else:
                    entry_dt = entry_ts
                if isinstance(exit_ts, str):
                    exit_dt = datetime.fromisoformat(exit_ts.replace("Z", "+00:00"))
                else:
                    exit_dt = exit_ts
                hold_minutes = (exit_dt - entry_dt).total_seconds() / 60
                hold_times.append(hold_minutes)
            except:
                pass

    hold_time_stats = {}
    if hold_times:
        hold_time_stats = {
            "min_minutes": round(min(hold_times), 2),
            "max_minutes": round(max(hold_times), 2),
            "avg_minutes": round(sum(hold_times) / len(hold_times), 2),
            "median_minutes": round(sorted(hold_times)[len(hold_times) // 2], 2)
        }

    # Best/Worst symbols
    symbol_list = [(s, d["pnl"], d["trades"]) for s, d in symbols.items()]
    symbol_list_sorted = sorted(symbol_list, key=lambda x: x[1], reverse=True)

    best_symbols = [{"symbol": s, "pnl": round(p, 4), "trades": t} for s, p, t in symbol_list_sorted[:5] if p > 0]
    worst_symbols = [{"symbol": s, "pnl": round(p, 4), "trades": t} for s, p, t in symbol_list_sorted[-5:] if p < 0]

    return {
        "exchange_name": exchange,
        "strategy_name": strategy,
        "source_file": filename,
        "total_trades": total_trades,
        "win_count": win_count,
        "loss_count": loss_count,
        "breakeven_count": breakeven_count,
        "win_rate": round(win_rate, 4),
        "total_pnl": round(total_pnl, 4),
        "avg_win": round(avg_win, 4),
        "avg_loss": round(avg_loss, 4),
        "profit_factor": round(abs(sum(t.get("pnl", 0) for t in wins) / sum(t.get("pnl", 0) for t in losses)), 4) if losses and sum(t.get("pnl", 0) for t in losses) != 0 else None,
        "symbols": {s: {"trades": d["trades"], "wins": d["wins"], "losses": d["losses"], "pnl": round(d["pnl"], 4)} for s, d in symbols.items()},
        "best_symbols": best_symbols,
        "worst_symbols": worst_symbols,
        "direction_stats": {
            "LONG": {
                "trades": direction_stats["LONG"]["trades"],
                "wins": direction_stats["LONG"]["wins"],
                "losses": direction_stats["LONG"]["losses"],
                "pnl": round(direction_stats["LONG"]["pnl"], 4),
                "win_rate": round(direction_stats["LONG"]["wins"] / direction_stats["LONG"]["trades"], 4) if direction_stats["LONG"]["trades"] > 0 else 0
            },
            "SHORT": {
                "trades": direction_stats["SHORT"]["trades"],
                "wins": direction_stats["SHORT"]["wins"],
                "losses": direction_stats["SHORT"]["losses"],
                "pnl": round(direction_stats["SHORT"]["pnl"], 4),
                "win_rate": round(direction_stats["SHORT"]["wins"] / direction_stats["SHORT"]["trades"], 4) if direction_stats["SHORT"]["trades"] > 0 else 0
            }
        },
        "confidence_calibration": confidence_calibration if has_confidence else None,
        "hold_time_stats": hold_time_stats if hold_time_stats else None,
        "date_range": {
            "first_trade": first_trade,
            "last_trade": last_trade
        }
    }


def main():
    """Main analysis function."""
    all_results = []

    # Get all JSON files
    trade_files = list(TRADES_DIR.glob("*.json"))
    archive_files = list(ARCHIVE_DIR.glob("*.json")) if ARCHIVE_DIR.exists() else []

    all_files = trade_files + archive_files

    print(f"Found {len(all_files)} trade files to analyze")
    print("-" * 60)

    for filepath in sorted(all_files):
        filename = filepath.name
        exchange, strategy = parse_strategy_from_filename(filename)

        try:
            with open(filepath, "r") as f:
                trades = json.load(f)

            if isinstance(trades, list):
                result = analyze_trades(trades, exchange, strategy, filename)
                if result:
                    all_results.append(result)
                    print(f"Analyzed: {filename}")
                    print(f"  Exchange: {exchange}, Strategy: {strategy}")
                    print(f"  Trades: {result['total_trades']}, Win Rate: {result['win_rate']:.2%}, P&L: ${result['total_pnl']:.2f}")
                else:
                    print(f"Skipped (no closed trades): {filename}")
            else:
                print(f"Skipped (not a list): {filename}")
        except Exception as e:
            print(f"Error processing {filename}: {e}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    # Aggregate stats
    total_all_trades = sum(r["total_trades"] for r in all_results)
    total_all_wins = sum(r["win_count"] for r in all_results)
    total_all_pnl = sum(r["total_pnl"] for r in all_results)

    print(f"\nTotal trade files analyzed: {len(all_results)}")
    print(f"Total trades across all files: {total_all_trades}")
    print(f"Overall win rate: {total_all_wins / total_all_trades:.2%}" if total_all_trades > 0 else "N/A")
    print(f"Total P&L: ${total_all_pnl:.2f}")

    # By exchange
    print("\n--- By Exchange ---")
    exchanges = defaultdict(lambda: {"trades": 0, "wins": 0, "pnl": 0})
    for r in all_results:
        ex = r["exchange_name"]
        exchanges[ex]["trades"] += r["total_trades"]
        exchanges[ex]["wins"] += r["win_count"]
        exchanges[ex]["pnl"] += r["total_pnl"]

    for ex, data in sorted(exchanges.items()):
        wr = data["wins"] / data["trades"] if data["trades"] > 0 else 0
        print(f"  {ex}: {data['trades']} trades, {wr:.2%} win rate, ${data['pnl']:.2f} P&L")

    # Save results
    output_path = TRADES_DIR / "analysis_summary.json"
    with open(output_path, "w") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "total_files_analyzed": len(all_results),
            "total_trades": total_all_trades,
            "overall_win_rate": round(total_all_wins / total_all_trades, 4) if total_all_trades > 0 else 0,
            "total_pnl": round(total_all_pnl, 4),
            "by_exchange": {ex: {"trades": d["trades"], "wins": d["wins"], "pnl": round(d["pnl"], 4), "win_rate": round(d["wins"] / d["trades"], 4) if d["trades"] > 0 else 0} for ex, d in exchanges.items()},
            "files": all_results
        }, f, indent=2, default=str)

    print(f"\nDetailed results saved to: {output_path}")

    return all_results


if __name__ == "__main__":
    main()
