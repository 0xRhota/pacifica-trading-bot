#!/usr/bin/env python3
"""
Bot Health Monitor - Billion-dollar infra standards
Checks that all critical systems are operational
"""
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

class BotMonitor:
    """Monitor bot health and log integrity"""

    CRITICAL_BOTS = {
        "pacifica": {
            "process": "live_pacifica.py",
            "log": "logs/pacifica.log",
            "max_silence_minutes": 2  # Should log every 45s
        },
        "lighter_vwap": {
            "process": "vwap_lighter_bot.py",
            "log": "logs/lighter_vwap.log",
            "max_silence_minutes": 6  # Should log every 5min
        }
    }

    def check_process_running(self, process_name: str) -> bool:
        """Check if process is running"""
        try:
            result = subprocess.run(
                ["pgrep", "-f", process_name],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception as e:
            print(f"❌ Error checking process {process_name}: {e}")
            return False

    def check_log_recent(self, log_path: str, max_minutes: int) -> tuple:
        """Check if log has been written to recently"""
        try:
            path = Path(log_path)
            if not path.exists():
                return False, "Log file does not exist"

            if path.stat().st_size == 0:
                return False, "Log file is empty"

            mod_time = datetime.fromtimestamp(path.stat().st_mtime)
            age_minutes = (datetime.now() - mod_time).total_seconds() / 60

            if age_minutes > max_minutes:
                return False, f"Last write {age_minutes:.1f}min ago (max {max_minutes}min)"

            return True, f"Last write {age_minutes:.1f}min ago ✓"
        except Exception as e:
            return False, f"Error: {e}"

    def check_all(self) -> dict:
        """Run all health checks"""
        results = {}
        all_healthy = True

        for bot_name, config in self.CRITICAL_BOTS.items():
            process_running = self.check_process_running(config["process"])
            log_ok, log_msg = self.check_log_recent(
                config["log"],
                config["max_silence_minutes"]
            )

            healthy = process_running and log_ok
            all_healthy = all_healthy and healthy

            results[bot_name] = {
                "healthy": healthy,
                "process_running": process_running,
                "log_status": log_msg,
                "config": config
            }

        return {
            "timestamp": datetime.now().isoformat(),
            "all_healthy": all_healthy,
            "bots": results
        }

    def print_status(self):
        """Print formatted status"""
        status = self.check_all()

        print("\n" + "=" * 70)
        print(f"🔍 BOT HEALTH CHECK - {status['timestamp']}")
        print("=" * 70)

        for bot_name, result in status["bots"].items():
            icon = "✅" if result["healthy"] else "❌"
            print(f"\n{icon} {bot_name.upper()}")
            print(f"   Process: {'RUNNING' if result['process_running'] else 'STOPPED'}")
            print(f"   Log: {result['log_status']}")

        print("\n" + "=" * 70)
        if status["all_healthy"]:
            print("✅ ALL SYSTEMS OPERATIONAL")
        else:
            print("❌ CRITICAL ISSUES DETECTED")
        print("=" * 70 + "\n")

        return status["all_healthy"]

if __name__ == "__main__":
    monitor = BotMonitor()
    healthy = monitor.print_status()
    exit(0 if healthy else 1)
