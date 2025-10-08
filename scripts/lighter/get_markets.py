#!/usr/bin/env python3
"""Get available markets from Lighter"""

import asyncio
import lighter

async def get_markets():
    client = lighter.ApiClient(configuration=lighter.Configuration(host='https://mainnet.zklighter.elliot.ai'))
    order_api = lighter.OrderApi(client)

    try:
        # Get all order books (markets)
        books = await order_api.order_books()
        print("Available Markets:")
        print(f"Total: {len(books.order_books) if hasattr(books, 'order_books') else 0}")
        print()

        if hasattr(books, 'order_books'):
            for i, book in enumerate(books.order_books):
                print(f"{i}: {book}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    await client.close()

asyncio.run(get_markets())
