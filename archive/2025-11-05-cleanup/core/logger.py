"""Unified logging system - LEAN, CLEAN, SCALABLE"""

import logging
import json
from datetime import datetime
from typing import Dict, Optional, Any
from pathlib import Path


class UnifiedLogger:
    """Unified logging format for all bots"""
    
    def __init__(self, bot_name: str, log_dir: str = "logs"):
        self.bot_name = bot_name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger(f"bot_{bot_name}")
        self.logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        self.logger.handlers = []
        
        # File handler (all levels)
        file_handler = logging.FileHandler(self.log_dir / f"{bot_name}.log")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] [%(component)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler (INFO+)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(component)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
    
    def _log(self, level: int, component: str, message: str, data: Optional[Dict[str, Any]] = None):
        """Internal logging method"""
        extra = {'component': component}
        
        # Format message with data if provided
        if data:
            data_str = ' | '.join([f"{k}={v}" for k, v in data.items()])
            full_message = f"{message} | {data_str}"
        else:
            full_message = message
        
        self.logger.log(level, full_message, extra=extra)
    
    def debug(self, message: str, component: str = "general", data: Optional[Dict] = None):
        """Log DEBUG message"""
        self._log(logging.DEBUG, component, message, data)
    
    def info(self, message: str, component: str = "general", data: Optional[Dict] = None):
        """Log INFO message"""
        self._log(logging.INFO, component, message, data)
    
    def warning(self, message: str, component: str = "general", data: Optional[Dict] = None):
        """Log WARNING message"""
        self._log(logging.WARNING, component, message, data)
    
    def error(self, message: str, component: str = "general", data: Optional[Dict] = None):
        """Log ERROR message"""
        self._log(logging.ERROR, component, message, data)
    
    def critical(self, message: str, component: str = "general", data: Optional[Dict] = None):
        """Log CRITICAL message"""
        self._log(logging.CRITICAL, component, message, data)


