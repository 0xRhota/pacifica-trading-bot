#!/usr/bin/env python3
"""
Watchdog Monitor - 6 hour autonomous monitoring
Checks all bots every 5 minutes, restarts crashed ones, logs status.
"""
import subprocess
import time
import os
import re
from datetime import datetime, timedelta

LOG_FILE = "logs/watchdog.log"
CHECK_INTERVAL_SECONDS = 300  # 5 minutes

# Run until 6 AM next morning
now = datetime.now()
end_target = now.replace(hour=6, minute=0, second=0, microsecond=0)
if end_target <= now:
    end_target += timedelta(days=1)
DURATION_HOURS = (end_target - now).total_seconds() / 3600

# Bot definitions: name, process grep pattern, restart command, log file
BOTS = [
    {
        "name": "Nado Grid MM (ETH)",
        "grep": "grid_mm_nado_v8.py",
        "restart": "nohup python3 scripts/grid_mm_nado_v8.py > logs/grid_mm_nado.log 2>&1 &",
        "log": "logs/grid_mm_nado.log",
    },
    {
        "name": "Paradex Grid MM (BTC)",
        "grep": "grid_mm_live.py",
        "restart": "nohup python3.11 scripts/grid_mm_live.py > logs/grid_mm_live.log 2>&1 &",
        "log": "logs/grid_mm_live.log",
    },
    {
        "name": "Hibachi Grid MM (BTC)",
        "grep": "grid_mm_hibachi.py",
        "restart": "nohup python3 -u scripts/grid_mm_hibachi.py > logs/grid_mm_hibachi.log 2>&1 &",
        "log": "logs/grid_mm_hibachi.log",
    },
    {
        "name": "Hibachi LLM (Strategy F)",
        "grep": "hibachi_agent.bot_hibachi",
        "restart": "nohup python3 -u -m hibachi_agent.bot_hibachi --live --strategy F --interval 600 > logs/hibachi_bot.log 2>&1 &",
        "log": "logs/hibachi_bot.log",
    },
    {
        "name": "Extended Grid MM (BTC)",
        "grep": "grid_mm_extended.py",
        "restart": "nohup python3.11 -u scripts/grid_mm_extended.py > logs/grid_mm_extended.log 2>&1 &",
        "log": "logs/grid_mm_extended.log",
    },
]


def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def is_running(grep_pattern):
    """Check if a process matching the pattern is running."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", grep_pattern],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except Exception:
        return False


def restart_bot(bot):
    """Restart a crashed bot."""
    log(f"  RESTARTING: {bot['name']}")
    try:
        subprocess.Popen(bot["restart"], shell=True)
        time.sleep(3)
        if is_running(bot["grep"]):
            log(f"  ✅ {bot['name']} restarted successfully")
            return True
        else:
            log(f"  ❌ {bot['name']} failed to restart")
            return False
    except Exception as e:
        log(f"  ❌ Restart error: {e}")
        return False


def get_last_lines(log_file, n=20):
    """Get last n lines of a log file."""
    try:
        result = subprocess.run(
            ["tail", f"-{n}", log_file],
            capture_output=True, text=True
        )
        return result.stdout
    except Exception:
        return ""


def extract_nado_stats(log_content):
    """Extract stats from Nado grid MM log."""
    stats = {}
    lines = log_content.split("\n")
    for line in reversed(lines):
        if "Spread:" in line and "bps" in line and "spread" not in stats:
            match = re.search(r"Spread:\s*([\d.]+)bps", line)
            if match:
                stats["spread"] = float(match.group(1))
        if "ROC:" in line and "roc" not in stats:
            match = re.search(r"ROC:\s*([+-]?[\d.]+)bps", line)
            if match:
                stats["roc"] = float(match.group(1))
        if "Fills:" in line and "fills" not in stats:
            match = re.search(r"Fills:\s*(\d+)", line)
            if match:
                stats["fills"] = int(match.group(1))
        if "Volume:" in line and "volume" not in stats:
            match = re.search(r"Volume:\s*\$([\d.]+)", line)
            if match:
                stats["volume"] = float(match.group(1))
        if "Position:" in line and "position" not in stats:
            match = re.search(r"Position:\s*([-\d.]+)", line)
            if match:
                stats["position"] = float(match.group(1))
        if "P&L:" in line and "balance" not in stats:
            match = re.search(r"\(\$([\d.]+)\)", line)
            if match:
                stats["balance"] = float(match.group(1))
    return stats


def extract_paradex_stats(log_content):
    """Extract stats from Paradex grid MM log."""
    stats = {}
    lines = log_content.split("\n")
    for line in reversed(lines):
        if "spread" in line.lower() and "bps" in line and "spread" not in stats:
            match = re.search(r"([\d.]+)\s*bps", line)
            if match:
                stats["spread"] = float(match.group(1))
        if "fills" in line.lower() and "fills" not in stats:
            match = re.search(r"[Ff]ills:\s*(\d+)", line)
            if match:
                stats["fills"] = int(match.group(1))
    return stats


def check_errors(log_file, since_minutes=5):
    """Check for recent errors in log file."""
    errors = []
    try:
        content = get_last_lines(log_file, 100)
        for line in content.split("\n"):
            if any(kw in line.lower() for kw in ["error", "exception", "traceback", "failed"]):
                if "cancel" not in line.lower():  # Ignore "no orders to cancel"
                    errors.append(line.strip())
    except Exception:
        pass
    return errors[-3:] if errors else []  # Last 3 errors only


def count_fills_since(log_file, minutes=60):
    """Count fills in the last N minutes from log."""
    count = 0
    try:
        content = get_last_lines(log_file, 500)
        cutoff = datetime.now() - timedelta(minutes=minutes)
        for line in content.split("\n"):
            if "FILL" in line.upper() or "Limit order created" in line:
                # Try to extract timestamp
                match = re.match(r"(\d{2}:\d{2}:\d{2})", line)
                if match:
                    try:
                        t = datetime.strptime(match.group(1), "%H:%M:%S").replace(
                            year=datetime.now().year,
                            month=datetime.now().month,
                            day=datetime.now().day
                        )
                        if t >= cutoff:
                            count += 1
                    except Exception:
                        pass
    except Exception:
        pass
    return count


def run_check():
    """Run one monitoring check cycle."""
    log("=" * 60)
    log("WATCHDOG CHECK")
    log("=" * 60)

    restarts = 0
    for bot in BOTS:
        running = is_running(bot["grep"])
        status = "✅ RUNNING" if running else "❌ DOWN"
        log(f"  {bot['name']}: {status}")

        if not running:
            restarts += 1
            restart_bot(bot)
            continue

        # Get stats from log
        log_content = get_last_lines(bot["log"], 50)

        if "nado" in bot["grep"]:
            stats = extract_nado_stats(log_content)
            if stats:
                parts = []
                if "spread" in stats:
                    parts.append(f"spread={stats['spread']}bps")
                if "roc" in stats:
                    parts.append(f"ROC={stats['roc']:+.1f}bps")
                if "fills" in stats:
                    parts.append(f"fills={stats['fills']}")
                if "volume" in stats:
                    parts.append(f"vol=${stats['volume']:.0f}")
                if "balance" in stats:
                    parts.append(f"bal=${stats['balance']:.2f}")
                if parts:
                    log(f"    Stats: {', '.join(parts)}")

                # Alert: zero fills for too long
                if stats.get("fills", 0) == 0 and stats.get("spread", 0) > 0:
                    log(f"    ⚠️  Zero fills - spread at {stats.get('spread', '?')} bps")

        elif "paradex" in bot["grep"] or "grid_mm_live" in bot["grep"]:
            stats = extract_paradex_stats(log_content)
            if stats:
                parts = []
                if "spread" in stats:
                    parts.append(f"spread={stats['spread']}bps")
                if "fills" in stats:
                    parts.append(f"fills={stats['fills']}")
                if parts:
                    log(f"    Stats: {', '.join(parts)}")

        # Check for errors
        errors = check_errors(bot["log"])
        if errors:
            log(f"    ⚠️  Recent errors ({len(errors)}):")
            for err in errors:
                log(f"      {err[:120]}")

    log(f"  Restarts this cycle: {restarts}")
    log("")


def main():
    log("")
    log("🐕 WATCHDOG STARTED - Monitoring for 6 hours")
    log(f"   Check interval: {CHECK_INTERVAL_SECONDS}s")
    log(f"   Bots monitored: {len(BOTS)}")
    log(f"   End time: {(datetime.now() + timedelta(hours=DURATION_HOURS)).strftime('%H:%M')}")
    log("")

    end_time = datetime.now() + timedelta(hours=DURATION_HOURS)
    checks = 0

    while datetime.now() < end_time:
        try:
            run_check()
            checks += 1
        except Exception as e:
            log(f"❌ Watchdog error: {e}")

        # Sleep until next check
        remaining = (end_time - datetime.now()).total_seconds()
        sleep_time = min(CHECK_INTERVAL_SECONDS, max(0, remaining))
        if sleep_time > 0:
            time.sleep(sleep_time)

    log("=" * 60)
    log(f"🐕 WATCHDOG COMPLETE - {checks} checks over {DURATION_HOURS} hours")
    log("=" * 60)


if __name__ == "__main__":
    main()
