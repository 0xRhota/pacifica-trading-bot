"""Unified Trading Bot - Works with any DEX adapter"""

import asyncio
import logging
import time
from typing import Dict, List, Optional
from dexes.base_adapter import BaseAdapter
from strategies.base_strategy import BaseStrategy
from core.startup_test import StartupTester, StartupError
from core.position_manager import PositionManager
from core.logger import UnifiedLogger

logger = logging.getLogger(__name__)


class UnifiedTradingBot:
    """Unified bot orchestrator - works with any DEX adapter"""
    
    def __init__(self, adapter: BaseAdapter, strategy: BaseStrategy, config: Dict):
        self.adapter = adapter
        self.strategy = strategy
        self.config = config
        self.logger = UnifiedLogger(config['bot_name'])
        self.position_manager = PositionManager(adapter, self.logger)
        self.startup_tester = StartupTester(self.logger)
        self.dry_run = config.get('dry_run', False)
        self.interval = config.get('interval', 300)
        
    async def initialize(self):
        """Initialize and validate everything"""
        self.logger.info("Initializing bot...", component="trading_bot")
        
        # 1. Initialize DEX adapter
        await self.adapter.initialize()
        
        # 2. Run startup tests
        try:
            data_fetcher = self.config.get('data_fetcher')
            await self.startup_tester.test_all(self.adapter, self.strategy, data_fetcher)
        except StartupError as e:
            self.logger.critical(f"Startup tests failed: {e}", component="trading_bot")
            raise
        
        # 3. Initialize position manager
        # (already done in __init__)
        
        # 4. Log ready
        self.logger.info("Bot initialized and validated", component="trading_bot", 
                        data={"status": "ready", "dry_run": self.dry_run})
    
    async def run_once(self):
        """Single decision cycle"""
        try:
            # 1. Fetch market data
            market_data = await self._fetch_market_data()
            
            if not market_data:
                self.logger.warning("No market data available", component="trading_bot")
                # Track consecutive failures
                if not hasattr(self, '_consecutive_empty_data'):
                    self._consecutive_empty_data = 0
                self._consecutive_empty_data += 1
                
                if self._consecutive_empty_data >= 3:
                    self.logger.critical(f"No market data for {self._consecutive_empty_data} consecutive cycles - possible exchange issue", 
                                       component="trading_bot")
                    # Consider: Send alert, pause trading, etc.
                return
            else:
                # Reset counter on success
                if hasattr(self, '_consecutive_empty_data'):
                    if self._consecutive_empty_data > 0:
                        self.logger.info(f"Market data restored after {self._consecutive_empty_data} failures", 
                                       component="trading_bot")
                    self._consecutive_empty_data = 0
            
            # 2. Fetch positions (with current prices updated) - THIS IS THE REAL STATE FROM EXCHANGE
            positions = await self.position_manager.get_positions()
            
            # 2.25. LOG REAL EXCHANGE STATE BEFORE ANYTHING
            self.logger.info(f"📊 REAL EXCHANGE STATE (before cycle): {len(positions)} positions", component="trading_bot")
            if positions:
                for pos in positions:
                    symbol = pos.get('symbol', 'UNKNOWN')
                    side = pos.get('side', 'UNKNOWN')
                    size = pos.get('size', 0)
                    entry = pos.get('entry_price', 0)
                    current = pos.get('current_price', 0)
                    pnl_pct = pos.get('pnl_pct', 0) or 0
                    self.logger.info(f"   {symbol} {side} | Size: {size:.4f} | Entry: ${entry:.4f} | Current: ${current:.4f} | P&L: {pnl_pct:+.2f}%", component="trading_bot")
            else:
                self.logger.info("   No open positions", component="trading_bot")
            
            # 2.5. Get failed executions from previous cycle (for LLM retry logic)
            failed_executions = getattr(self, '_last_failed_executions', [])
            
            # 3. Get context
            context = await self._build_context(market_data, positions, failed_executions)
            
            # 4. Add market table with all indicators to context (for LLM strategy)
            context['market_table'] = self._format_market_table_with_all_indicators(market_data)
            context['analyzed_tokens'] = list(market_data.keys())  # List of symbols for LLM prompt
            self.logger.debug(f"🔍 run_once: context['dex_name']={context.get('dex_name')}, markets={len(market_data)}", component="trading_bot")
            
            # 5. Get decisions from strategy
            self.logger.debug(f"Calling strategy.get_decisions() with {len(market_data)} markets, {len(positions)} positions", component="trading_bot")
            decisions = await self.strategy.get_decisions(market_data, positions, context)
            self.logger.debug(f"Strategy returned {len(decisions) if decisions else 0} decisions", component="trading_bot")
            
            if not decisions:
                self.logger.info("No decisions from strategy", component="trading_bot")
                return
            
            # 6. Cross-reference decisions with actual data
            validated_decisions = self._validate_decisions(decisions, positions)
            
            if not validated_decisions:
                self.logger.info("No validated decisions after cross-reference", component="trading_bot")
                return
            
            # 7. Execute decisions
            self.logger.info(f"🔄 ATTEMPTING {len(validated_decisions)} trades:", component="trading_bot")
            for decision in validated_decisions:
                action = decision.get('action', '').upper()
                symbol = decision.get('symbol', 'UNKNOWN')
                self.logger.info(f"   → {action} {symbol}", component="trading_bot")
            
            results = await self._execute_decisions(validated_decisions)
            
            # 7.5. SYNC REAL STATE FROM EXCHANGE - Show what ACTUALLY changed
            await asyncio.sleep(2.0)  # Give exchange time to update
            positions_after = await self.adapter.get_positions()
            self.logger.info(f"📊 REAL EXCHANGE STATE (after cycle): {len(positions_after)} positions", component="trading_bot")
            for pos in positions_after:
                symbol = pos.get('symbol', 'UNKNOWN')
                side = pos.get('side', 'UNKNOWN')
                size = pos.get('size', 0)
                pnl_pct = pos.get('pnl_pct', 0) or 0
                self.logger.info(f"   {symbol} {side} | Size: {size:.4f} | P&L: {pnl_pct:+.2f}%", component="trading_bot")
            
            # Count what actually happened
            filled = sum(1 for r in results if r.get('success') and r.get('fill_verified'))
            submitted_not_filled = sum(1 for r in results if r.get('success') and not r.get('fill_verified'))
            failed = sum(1 for r in results if not r.get('success'))
            
            # Show actual results
            self.logger.info(f"📈 EXECUTION RESULTS: {filled} FILLED | {submitted_not_filled} SUBMITTED BUT NOT FILLED | {failed} FAILED", component="trading_bot")
            
            # 7.6. Store failed executions for next cycle (LLM retry logic)
            # ✅ ONLY include temporary failures (slippage, transient errors)
            # ✅ EXCLUDE permanent failures (minimum_size_violation, uncloseable_position, margin_mode_error)
            # This prevents infinite retry loops on structurally invalid orders
            PERMANENT_ERROR_TYPES = {'minimum_size_violation', 'uncloseable_position', 'margin_mode_error'}

            self._last_failed_executions = [
                {
                    'symbol': r.get('symbol'),
                    'action': r.get('action'),
                    'error': r.get('error'),
                    'error_type': r.get('error_type'),
                    'error_details': r.get('error_details'),
                    'current_price': r.get('current_price'),
                    'retryable': r.get('retryable', False)
                }
                for r in results
                if not r.get('success')
                and r.get('retryable')
                and r.get('error_type') not in PERMANENT_ERROR_TYPES
            ]
            
            # 8. Log everything
            self._log_cycle(market_data, positions_after, decisions, results)
            
        except Exception as e:
            self.logger.error(f"Error in decision cycle: {e}", component="trading_bot")
            import traceback
            self.logger.error(traceback.format_exc(), component="trading_bot")
    
    async def _fetch_market_data(self) -> Dict:
        """Fetch market data for all active markets"""
        markets = self.adapter.get_active_markets()
        
        # Filter to allowed tokens if specified in config
        allowed_tokens = self.config.get('allowed_tokens')
        if allowed_tokens:
            # Only fetch markets that are in the whitelist
            markets = [m for m in markets if m in allowed_tokens]
            self.logger.debug(f"Filtered to {len(markets)} allowed tokens: {allowed_tokens}", component="trading_bot")
        
        # Fetch markets (now filtered to whitelist if specified)
        markets_to_fetch = list(markets)
        
        if not markets_to_fetch:
            self.logger.warning("No markets to fetch", component="trading_bot")
            return {}
        
        market_data = {}
        
        # Fetch data for markets in parallel
        import asyncio
        tasks = [self.adapter.get_market_data(symbol) for symbol in markets_to_fetch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = 0
        for symbol, data in zip(markets_to_fetch, results):
            if isinstance(data, Exception):
                self.logger.debug(f"Error fetching data for {symbol}: {type(data).__name__}", component="trading_bot")
                continue
            if data:
                market_data[symbol] = data
                successful += 1
        
        if successful > 0:
            self.logger.info(f"Fetched market data for {successful}/{len(markets_to_fetch)} markets", component="trading_bot")
        else:
            self.logger.warning(f"No market data fetched for any of {len(markets_to_fetch)} markets", component="trading_bot")
        
        return market_data
    
    async def _build_context(self, market_data: Dict, positions: List[Dict], failed_executions: List[Dict] = None) -> Dict:
        """Build context for strategy"""
        balance = await self.adapter.get_balance()
        recently_closed = self.position_manager.get_recently_closed_symbols(hours=2)
        
        # Track failed executions for LLM retry logic
        if failed_executions is None:
            failed_executions = []
        
        # Get DEX name from adapter (if available) or default to bot name
        # Handle None/empty bot_name defensively - ALWAYS set a value
        bot_name = self.config.get('bot_name')
        if not bot_name or not isinstance(bot_name, str) or not bot_name.strip():
            # Fallback: try to infer from adapter class name or default to 'Pacifica'
            adapter_name = type(self.adapter).__name__.lower()
            if 'lighter' in adapter_name:
                bot_name = 'lighter'
            else:
                bot_name = 'pacifica'
        
        # Capitalize properly
        bot_name = bot_name.strip().capitalize()
        
        # Use adapter's dex_name if available, otherwise infer from bot_name or adapter class
        dex_name = getattr(self.adapter, 'dex_name', None)
        if not dex_name or not isinstance(dex_name, str) or not dex_name.strip():
            # Infer from bot_name (e.g., "lighter" -> "Lighter", "pacifica" -> "Pacifica")
            if bot_name and isinstance(bot_name, str):
                dex_name = bot_name.capitalize()
            else:
                # Last resort: infer from adapter class name
                adapter_class_name = self.adapter.__class__.__name__
                if 'Lighter' in adapter_class_name:
                    dex_name = 'Lighter'
                elif 'Pacifica' in adapter_class_name:
                    dex_name = 'Pacifica'
                else:
                    dex_name = 'DEX'  # Generic fallback (NEVER use "Pacifica" as default)
        
        self.logger.debug(f"🔍 _build_context: dex_name={dex_name}, bot_name from config={self.config.get('bot_name')}, adapter.has_dex_name={hasattr(self.adapter, 'dex_name')}", component="trading_bot")
        
        # Get trade history
        trade_history = ""
        recent_trades = self.position_manager.tracker.get_recent_trades(hours=24, limit=10)
        if recent_trades:
            trade_history = "\n\nRECENT TRADING HISTORY (Last 24h):\n"
            trade_history += "Symbol | Side | Entry Price | Exit Price | P&L | Status\n"
            trade_history += "-" * 70 + "\n"
            for trade in recent_trades[-10:]:
                symbol = trade.get('symbol') or 'N/A'
                side = (trade.get('side') or 'N/A').upper()
                entry = trade.get('entry_price') or 0
                exit_price = trade.get('exit_price')
                pnl = trade.get('pnl') or 0
                status = trade.get('status') or 'N/A'
                exit_str = f"${exit_price:.4f}" if exit_price and exit_price != 'N/A' else 'N/A'
                trade_history += f"{symbol} | {side} | ${entry:.4f} | {exit_str} | ${pnl:.2f} | {status}\n"
        
        return {
            'account_balance': balance,
            'recently_closed_symbols': recently_closed,
            'trade_history': trade_history,
            'max_positions': self.config.get('max_positions', 15),
            'macro_context': self.config.get('macro_context', ''),
            'market_table': '',  # Set in run_once() after market data is fetched
            'deep42_context': self.config.get('deep42_context'),
            'hourly_review': self.config.get('hourly_review'),
            'dex_name': dex_name,  # Pass DEX name for dynamic prompts
            'failed_executions': failed_executions  # Pass failed executions for LLM retry decisions
        }
    
    def _validate_decisions(self, decisions: List[Dict], positions: List[Dict]) -> List[Dict]:
        """Cross-reference LLM decisions with actual data"""
        validated = []
        markets = set(self.adapter.get_active_markets())
        position_symbols = {p['symbol'] for p in positions}
        
        for decision in decisions:
            symbol = decision.get('symbol')
            action = decision.get('action', '').upper()
            
            # Check: Is symbol in allowed tokens whitelist (if specified)?
            # IMPORTANT: CLOSE orders are ALWAYS allowed (need to close existing positions even if not in whitelist)
            allowed_tokens = self.config.get('allowed_tokens')
            if allowed_tokens and action != "CLOSE" and symbol not in allowed_tokens:
                self.logger.warning(f"Skipping {action} {symbol} - not in allowed tokens whitelist", 
                                   component="validator",
                                   data={"symbol": symbol, "decision": decision, "allowed": allowed_tokens})
                continue
            
            # Check: Does symbol exist in markets?
            if symbol not in markets:
                self.logger.warning("Invalid symbol in decision", 
                                   component="validator",
                                   data={"symbol": symbol, "decision": decision})
                continue
            
            # Check: Does position exist if CLOSE?
            if action == 'CLOSE':
                if symbol not in position_symbols:
                    self.logger.warning("CLOSE on non-existent position", 
                                       component="validator",
                                       data={"symbol": symbol, "decision": decision})
                    continue
            
            # Check: Already have position if BUY/SELL?
            if action in ['BUY', 'SELL']:
                if symbol in position_symbols:
                    self.logger.info(f"Skipping {action} {symbol} - already have position", 
                                    component="validator")
                    continue
            
            validated.append(decision)
        
        return validated
    
    async def _execute_decisions(self, decisions: List[Dict]) -> List[Dict]:
        """Execute validated decisions"""
        results = []
        executor = self.config.get('executor')
        
        if not executor:
            self.logger.warning("No executor configured", component="trading_bot")
            return results
        
        for decision in decisions:
            try:
                result = await executor.execute_decision(decision, self.dry_run)
                results.append(result)
                
                # If execution failed with retryable error (e.g., slippage), log it for LLM analysis
                # The LLM will see this in the next cycle and can decide to retry or adjust
                if not result.get('success') and result.get('retryable'):
                    self.logger.warning(
                        f"⚠️ Retryable execution failure for {decision['action']} {decision['symbol']}: {result.get('error')} | "
                        f"LLM can retry this in next cycle with updated price",
                        component="trading_bot",
                        data={
                            "error_type": result.get('error_type'),
                            "error_details": result.get('error_details'),
                            "current_price": result.get('current_price')
                        }
                    )
                
                # Log entry/exit
                if result.get('success'):
                    if decision['action'] in ['BUY', 'SELL']:
                        # Get order_id from result (persisted in TradeTracker)
                        order_id = result.get('tx_hash') or result.get('order_id') or f"order_{decision['symbol']}_{int(time.time())}"
                        # Store order_id in TradeTracker (persistent storage)
                        trade_id = self.position_manager.log_entry(
                            decision['symbol'],
                            decision['action'],
                            result.get('entry_price', 0),
                            result.get('size', 0),
                            order_id=order_id
                        )
                    elif decision['action'] == 'CLOSE':
                        # Get order_id from TradeTracker (persistent storage, survives restarts)
                        order_id = self.position_manager.get_order_id_for_symbol(decision['symbol'])
                        if not order_id:
                            # Fallback: use result order_id if TradeTracker doesn't have it
                            order_id = result.get('tx_hash') or result.get('order_id') or f"close_{decision['symbol']}_{int(time.time())}"
                            self.logger.warning(f"Could not find order_id for {decision['symbol']} in TradeTracker, using fallback", 
                                              component="trading_bot")
                        
                        self.position_manager.log_exit(
                            order_id,
                            result.get('exit_price', 0),
                            result.get('pnl', 0),
                            exit_reason=f"Closed {decision['symbol']}"
                        )
            except Exception as e:
                self.logger.error(f"Error executing decision: {e}", 
                                component="executor",
                                data={"decision": decision})
                results.append({"success": False, "error": str(e)})
        
        return results
    
    def _format_market_table_with_all_indicators(self, market_data: Dict) -> str:
        """Format market data table with all 5m and 4h indicators"""
        lines = []
        lines.append("Market Data (Latest):")
        lines.append("=" * 120)
        lines.append(
            f"{'Symbol':<10} {'Price':>12} {'24h Vol':>12} "
            f"{'RSI':>6} {'EMA20':>10} {'MACD':>8} {'BB Width':>10} {'Stoch K':>8} {'4h EMA':>10} {'ATR':>10} {'ADX':>6}"
        )
        lines.append("-" * 120)

        for symbol, data in sorted(market_data.items()):
            if not data:
                continue

            indicators = data.get('indicators', {})
            price = data.get('price', 0)
            volume = data.get('volume_24h', 0)

            # 5m indicators
            rsi = indicators.get('rsi')
            ema_20 = indicators.get('ema_20')
            macd = indicators.get('macd')
            bb_width = indicators.get('bb_width')
            stoch_k = indicators.get('stoch_k')

            # 4h indicators
            ema_20_4h = indicators.get('4h_ema_20')
            atr = indicators.get('4h_atr')
            adx = indicators.get('4h_adx')

            # Format values
            price_str = f"${price:,.2f}" if price else "N/A"
            volume_str = f"${volume/1000:.0f}K" if volume else "N/A"
            rsi_str = f"{rsi:.1f}" if rsi is not None else "N/A"
            ema_str = f"${ema_20:.2f}" if ema_20 is not None else "N/A"
            macd_str = f"{macd:+.4f}" if macd is not None else "N/A"
            bb_str = f"{bb_width:.2f}" if bb_width is not None else "N/A"
            stoch_str = f"{stoch_k:.1f}" if stoch_k is not None else "N/A"
            ema_4h_str = f"${ema_20_4h:.2f}" if ema_20_4h is not None else "N/A"
            atr_str = f"{atr:.2f}" if atr is not None else "N/A"
            adx_str = f"{adx:.1f}" if adx is not None else "N/A"

            lines.append(
                f"{symbol:<10} {price_str:>12} {volume_str:>12} "
                f"{rsi_str:>6} {ema_str:>10} {macd_str:>8} {bb_str:>10} {stoch_str:>8} "
                f"{ema_4h_str:>10} {atr_str:>10} {adx_str:>6}"
            )

        return "\n".join(lines)

    def _log_cycle(self, market_data: Dict, positions: List[Dict], decisions: List[Dict], results: List[Dict]):
        """Log decision cycle - show REAL results"""
        filled = sum(1 for r in results if r.get('success') and r.get('fill_verified'))
        submitted_not_filled = sum(1 for r in results if r.get('success') and not r.get('fill_verified'))
        failed = sum(1 for r in results if not r.get('success'))
        
        self.logger.info(
            f"✅ CYCLE COMPLETE | Markets: {len(market_data)} | Positions: {len(positions)} | "
            f"Decisions: {len(decisions)} | FILLED: {filled} | SUBMITTED BUT NOT FILLED: {submitted_not_filled} | FAILED: {failed}",
            component="trading_bot"
        )
    
    async def run(self):
        """Main bot loop"""
        while True:
            await self.run_once()
            self.logger.info(f"Sleeping for {self.interval} seconds until next cycle...", component="trading_bot")
            await asyncio.sleep(self.interval)

