"""
Delta-Neutral Funding Rate Arbitrage Agent
==========================================
Exploits funding rate differentials between two perpetual exchanges
while maintaining delta-neutral exposure.

Strategy:
- Monitor funding rates on both exchanges
- When spread exceeds threshold: SHORT high-rate exchange, LONG low-rate exchange
- Collect funding differential every 8 hours
- Rebalance positions to maintain delta neutrality

Supported Exchanges:
- Hibachi (Arbitrum)
- Extended (Starknet)
- Easily extensible to other exchanges
"""
