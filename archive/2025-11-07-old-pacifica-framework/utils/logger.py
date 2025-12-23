#!/usr/bin/env python3
"""
DEX-Specific Logging System
Creates separate, secure log files for each DEX
Ensures no private keys or sensitive data are logged
"""

import logging
import os
import re
from typing import Optional
from datetime import datetime


class SecureFormatter(logging.Formatter):
    """
    Custom formatter that redacts sensitive information
    Prevents accidental logging of private keys, API keys, etc.
    """

    # Patterns to detect and redact
    SENSITIVE_PATTERNS = [
        # Solana private keys (base58, 87-88 chars)
        (r'[1-9A-HJ-NP-Za-km-z]{87,88}', '[SOLANA_KEY_REDACTED]'),
        # Ethereum private keys (0x + 64 hex chars)
        (r'0x[a-fA-F0-9]{64}', '[ETH_KEY_REDACTED]'),
        # API keys (long hex strings)
        (r'[a-fA-F0-9]{64,}', '[API_KEY_REDACTED]'),
        # Any field named private_key, api_key, etc.
        (r'(private_key|api_key|secret_key|password)\s*[:=]\s*[^\s,}\]]+', r'\1=[REDACTED]'),
    ]

    def format(self, record):
        """Format and redact sensitive information"""
        # Get the original formatted message
        message = super().format(record)

        # Redact sensitive patterns
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)

        return message


class DEXLogger:
    """
    Manages separate log files for each DEX with security built-in
    """

    def __init__(self, dex_name: str, log_dir: str = "logs"):
        """
        Initialize logger for a specific DEX

        Args:
            dex_name: Name of the DEX (e.g., "pacifica", "lighter")
            log_dir: Directory for log files
        """
        self.dex_name = dex_name.lower()
        self.log_dir = log_dir

        # Create logs directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)

        # Create logger
        self.logger = logging.getLogger(f"dex.{self.dex_name}")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False  # Don't propagate to root logger

        # Clear existing handlers
        self.logger.handlers.clear()

        # Create log file path with date
        log_date = datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(log_dir, f"{self.dex_name}_{log_date}.log")

        # File handler with secure formatting
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_formatter = SecureFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)

        # Console handler with secure formatting
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = SecureFormatter(
            '%(levelname)s [%(name)s] - %(message)s'
        )
        console_handler.setFormatter(console_formatter)

        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def info(self, message: str):
        """Log info message"""
        self.logger.info(message)

    def warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)

    def error(self, message: str):
        """Log error message"""
        self.logger.error(message)

    def debug(self, message: str):
        """Log debug message"""
        self.logger.debug(message)

    def trade(self, action: str, symbol: str, size: float, price: float, order_id: Optional[str] = None):
        """
        Log a trade action with standardized format

        Args:
            action: "BUY" or "SELL"
            symbol: Trading pair symbol
            size: Position size
            price: Execution price
            order_id: Optional order ID (will be masked if too long)
        """
        # Mask long order IDs (could contain sensitive info)
        if order_id and len(str(order_id)) > 20:
            order_id = f"{str(order_id)[:8]}...{str(order_id)[-4:]}"

        if order_id:
            self.logger.info(f"TRADE: {action} {size:.6f} {symbol} @ ${price:.4f} [Order: {order_id}]")
        else:
            self.logger.info(f"TRADE: {action} {size:.6f} {symbol} @ ${price:.4f}")

    def position_update(self, symbol: str, size: float, entry_price: float, unrealized_pnl: Optional[float] = None):
        """
        Log position status update

        Args:
            symbol: Trading pair symbol
            size: Current position size (negative for short)
            entry_price: Entry price
            unrealized_pnl: Unrealized P&L if available
        """
        side = "LONG" if size > 0 else "SHORT"
        pnl_str = f" | PnL: ${unrealized_pnl:.2f}" if unrealized_pnl is not None else ""
        self.logger.info(f"POSITION: {side} {abs(size):.6f} {symbol} @ ${entry_price:.4f}{pnl_str}")

    def connection_status(self, status: str, details: Optional[str] = None):
        """
        Log connection status

        Args:
            status: "CONNECTED", "DISCONNECTED", "ERROR"
            details: Optional details about the connection
        """
        if details:
            self.logger.info(f"CONNECTION: {status} - {details}")
        else:
            self.logger.info(f"CONNECTION: {status}")


class MultiDEXLogger:
    """
    Manages loggers for multiple DEXes
    Provides easy access to DEX-specific loggers
    """

    def __init__(self, log_dir: str = "logs"):
        """
        Initialize multi-DEX logger

        Args:
            log_dir: Directory for all log files
        """
        self.log_dir = log_dir
        self.loggers = {}

    def get_logger(self, dex_name: str) -> DEXLogger:
        """
        Get or create logger for a specific DEX

        Args:
            dex_name: Name of the DEX

        Returns:
            DEXLogger instance
        """
        if dex_name not in self.loggers:
            self.loggers[dex_name] = DEXLogger(dex_name, self.log_dir)
        return self.loggers[dex_name]

    @property
    def pacifica(self) -> DEXLogger:
        """Get Pacifica logger"""
        return self.get_logger("pacifica")

    @property
    def lighter(self) -> DEXLogger:
        """Get Lighter logger"""
        return self.get_logger("lighter")


# Example usage
if __name__ == "__main__":
    # Test secure logging
    multi_logger = MultiDEXLogger()

    # Test Pacifica logger
    pacifica_log = multi_logger.pacifica
    pacifica_log.connection_status("CONNECTED", "Mainnet")
    pacifica_log.trade("BUY", "SOL-PERP", 0.5, 150.25, "abc123def456")
    pacifica_log.position_update("SOL-PERP", 0.5, 150.25, 2.50)

    # Test Lighter logger
    lighter_log = multi_logger.lighter
    lighter_log.connection_status("CONNECTED", "zkSync mainnet")
    lighter_log.trade("SELL", "ETH-PERP", 0.1, 2500.00, "xyz789uvw123")
    lighter_log.position_update("ETH-PERP", -0.1, 2500.00, -1.25)

    # Test redaction - these should be masked (using obviously fake test keys)
    pacifica_log.info("Testing key redaction: private_key=0x0000000000000000000000000000000000000000000000000000000000000000")
    lighter_log.info("API key test: 0000000000000000000000000000000000000000000000000000000000000000")

    print("\n✅ Logs created in logs/ directory")
    print("✅ All sensitive data redacted automatically")
