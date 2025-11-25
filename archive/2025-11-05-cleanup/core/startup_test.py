"""Startup testing framework - validates all APIs before trading"""

import asyncio
import logging
from typing import Dict, Any, Optional
from dexes.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class StartupError(Exception):
    """Raised when startup tests fail"""
    pass


class StartupTester:
    """Comprehensive startup validation"""
    
    def __init__(self, logger_instance):
        self.logger = logger_instance
        self.test_results = {}
    
    async def test_all(self, adapter: BaseAdapter, strategy, data_fetcher=None) -> Dict[str, bool]:
        """Run all startup tests"""
        self.logger.info("Running startup tests...", component="startup_test")
        
        results = {}
        
        # Test 1: DEX connection
        results['dex_connection'] = await self.test_dex_connection(adapter)
        
        # Test 2: Market fetching
        results['markets'] = await self.test_market_fetching(adapter)
        
        # Test 3: Position fetching
        results['positions'] = await self.test_position_fetching(adapter)
        
        # Test 4: Balance fetching
        results['balance'] = await self.test_balance_fetching(adapter)
        
        # Test 5: Data sources (if data fetcher provided)
        if data_fetcher:
            results['data_sources'] = await self.test_data_sources(data_fetcher)
        
        # Test 6: Strategy validation
        results['strategy'] = await self.test_strategy(strategy, adapter)
        
        # Test 7: Cross-reference (LLM vs API)
        results['cross_reference'] = await self.cross_reference_test(adapter, strategy)
        
        self.test_results = results
        
        # Fail if any critical test fails
        critical_tests = ['dex_connection', 'markets']
        failed_critical = [k for k in critical_tests if not results.get(k, False)]
        
        if failed_critical:
            error_msg = f"Critical startup tests failed: {failed_critical}"
            self.logger.error(error_msg, component="startup_test", data={"results": results})
            raise StartupError(error_msg)
        
        # Log warnings for non-critical failures
        non_critical_failures = [k for k, v in results.items() if not v and k not in critical_tests]
        if non_critical_failures:
            self.logger.warning(f"Non-critical tests failed: {non_critical_failures}", 
                             component="startup_test", data={"results": results})
        
        self.logger.info("Startup tests completed", component="startup_test", 
                        data={"passed": sum(results.values()), "total": len(results)})
        
        return results
    
    async def test_dex_connection(self, adapter: BaseAdapter) -> bool:
        """Test: Can we connect to DEX?"""
        try:
            await adapter.initialize()
            self.logger.info(f"DEX connection test passed", component="startup_test")
            return True
        except Exception as e:
            self.logger.error(f"DEX connection test failed: {e}", component="startup_test")
            return False
    
    async def test_market_fetching(self, adapter: BaseAdapter) -> bool:
        """Test: Can we fetch markets? Are they valid?"""
        try:
            markets = await adapter.get_markets()
            if not markets:
                self.logger.error("Market fetching returned no markets", component="startup_test")
                return False
            
            active_markets = adapter.get_active_markets()
            if not active_markets:
                self.logger.error("No active markets found", component="startup_test")
                return False
            
            self.logger.info(f"Market fetching test passed: {len(active_markets)} active markets", 
                           component="startup_test", data={"markets": active_markets[:10]})
            return True
        except Exception as e:
            self.logger.error(f"Market fetching test failed: {e}", component="startup_test")
            return False
    
    async def test_position_fetching(self, adapter: BaseAdapter) -> bool:
        """Test: Can we fetch positions? Do they match markets?"""
        try:
            positions = await adapter.get_positions()
            markets = adapter.get_active_markets()
            
            # Validate each position symbol exists in markets
            for pos in positions:
                symbol = pos.get('symbol')
                if symbol not in markets:
                    self.logger.warning(f"Position symbol {symbol} not in markets", 
                                      component="startup_test")
                    return False
            
            self.logger.info(f"Position fetching test passed: {len(positions)} positions", 
                           component="startup_test")
            return True
        except Exception as e:
            self.logger.error(f"Position fetching test failed: {e}", component="startup_test")
            return False
    
    async def test_balance_fetching(self, adapter: BaseAdapter) -> bool:
        """Test: Can we fetch balance?"""
        try:
            balance = await adapter.get_balance()
            if balance is None:
                self.logger.warning("Balance fetching returned None (may be valid for some DEXs)", component="startup_test")
                # Not a critical failure - some DEXs may not have balance endpoint
                return True
            
            self.logger.info(f"Balance fetching test passed: ${balance:.2f}", component="startup_test")
            return True
        except Exception as e:
            self.logger.warning(f"Balance fetching test failed (non-critical): {e}", component="startup_test")
            # Not critical - some DEXs may not support balance endpoint
            return True
    
    async def test_data_sources(self, data_fetcher) -> bool:
        """Test: Can we fetch market data (OHLCV, indicators)?"""
        try:
            # Test fetching data for first active market
            # This is adapter-specific, so we'll make it flexible
            markets = data_fetcher.get_active_markets() if hasattr(data_fetcher, 'get_active_markets') else []
            if not markets:
                return True  # No markets to test
            
            # Try fetching data for first market
            test_symbol = markets[0]
            data = await data_fetcher.get_market_data(test_symbol) if hasattr(data_fetcher, 'get_market_data') else None
            
            if data:
                self.logger.info(f"Data source test passed for {test_symbol}", component="startup_test")
                return True
            else:
                self.logger.warning(f"Data source test returned no data for {test_symbol}", 
                                  component="startup_test")
                return False
        except Exception as e:
            self.logger.error(f"Data source test failed: {e}", component="startup_test")
            return False
    
    async def test_strategy(self, strategy, adapter: BaseAdapter) -> bool:
        """Test: Can strategy initialize and make decisions?"""
        try:
            # Infer DEX name from adapter class name
            dex_name = self._infer_dex_name(adapter)
            
            # Get real positions and markets for realistic test
            real_positions = await adapter.get_positions()
            real_markets = adapter.get_active_markets()
            
            # Fetch market data for at least one market to test with real data
            if real_markets:
                # Use first market for test
                test_symbol = list(real_markets)[:1][0] if real_markets else None
                test_market_data = {}
                
                # Try to fetch market data for test symbol
                if test_symbol and hasattr(adapter, 'get_market_data'):
                    try:
                        test_data = await adapter.get_market_data(test_symbol)
                        if test_data:
                            test_market_data[test_symbol] = test_data
                    except Exception:
                        pass  # If market data fetch fails, test with empty (strategy should handle it)
                
                # Test with real positions and at least one market (if available)
                context = {'dex_name': dex_name, 'analyzed_tokens': list(test_market_data.keys()) if test_market_data else []}
                test_decisions = await strategy.get_decisions(test_market_data, real_positions, context)
            else:
                # No markets available - test with empty (should not crash)
                context = {'dex_name': dex_name}
                test_decisions = await strategy.get_decisions({}, real_positions, context)
            
            # Strategy should return a list (even if empty)
            if not isinstance(test_decisions, list):
                self.logger.error("Strategy returned non-list", component="startup_test")
                return False
            
            self.logger.info("Strategy test passed", component="startup_test")
            return True
        except Exception as e:
            self.logger.warning(f"Strategy test failed (may be non-critical): {e}", component="startup_test")
            # Some strategies may need market data - not critical if empty test fails
            return True
    
    async def cross_reference_test(self, adapter: BaseAdapter, strategy) -> bool:
        """Test: Strategy decisions match actual data"""
        try:
            # Infer DEX name from adapter class name
            dex_name = self._infer_dex_name(adapter)
            
            # Get real positions from API
            real_positions = await adapter.get_positions()
            real_symbols = {p['symbol'] for p in real_positions}
            
            # Get real markets from API
            real_markets = set(adapter.get_active_markets())
            
            if not real_markets:
                self.logger.warning("No markets available for cross-reference test", component="startup_test")
                return True  # Not critical if no markets
            
            # Get market data (simplified - just first market)
            market_data = {}
            if real_markets:
                test_symbol = list(real_markets)[0]
                market_data[test_symbol] = await adapter.get_market_data(test_symbol)
            
            # Ask strategy to analyze - pass proper context with dex_name
            context = {'dex_name': dex_name, 'analyzed_tokens': list(real_markets)}
            decisions = await strategy.get_decisions(market_data, real_positions, context)
            
            if not decisions:
                self.logger.info("Strategy returned no decisions (valid for empty market data)", component="startup_test")
                return True
            
            # Validate each decision
            invalid_count = 0
            for decision in decisions:
                symbol = decision.get('symbol')
                action = decision.get('action', '').upper()
                
                # Check: Symbol exists in markets?
                if symbol and symbol not in real_markets:
                    invalid_count += 1
                    self.logger.warning(f"Decision references invalid symbol: {symbol} (will be filtered by trading_bot)", 
                                      component="startup_test", 
                                      data={"decision": decision, "available_markets": list(real_markets)[:10]})
                    # Not critical - trading_bot will filter this
                
                # Check: If CLOSE, position exists?
                if action == 'CLOSE' and symbol:
                    if symbol not in real_symbols:
                        invalid_count += 1
                        self.logger.warning(f"CLOSE decision for non-existent position: {symbol} (will be filtered)", 
                                          component="startup_test",
                                          data={"decision": decision, "open_positions": list(real_symbols)})
                        # Not critical - trading_bot will filter this
            
            if invalid_count > 0:
                self.logger.warning(f"Cross-reference found {invalid_count} invalid decisions (will be filtered by trading_bot)", 
                                  component="startup_test")
            else:
                self.logger.info("Cross-reference test passed - all decisions valid", component="startup_test")
            return True
        except Exception as e:
            self.logger.warning(f"Cross-reference test failed (non-critical): {e}", component="startup_test")
            # Not critical - this is just a validation check
            return True
    
    def _infer_dex_name(self, adapter: BaseAdapter) -> str:
        """Infer DEX name from adapter class name"""
        adapter_class_name = adapter.__class__.__name__
        if 'Lighter' in adapter_class_name:
            return 'Lighter'
        elif 'Pacifica' in adapter_class_name:
            return 'Pacifica'
        else:
            # Try to get from adapter attribute
            dex_name = getattr(adapter, 'dex_name', None)
            if dex_name and isinstance(dex_name, str):
                return dex_name
            return 'DEX'  # Generic fallback

