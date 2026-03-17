"""
Binance WebSocket feed — streams real-time BTC/USDT trade price.
Stores the latest price in a shared asyncio-safe variable.
"""

import asyncio
import json
import aiohttp
from config import BINANCE_WS_URL
from utils.proxy import get_aiohttp_connector

# Shared state — read by the strategy module
latest_btc_price: float = 0.0
_lock = asyncio.Lock()


async def get_btc_price() -> float:
    async with _lock:
        return latest_btc_price


async def run_btc_feed():
    """Connects to Binance WebSocket and continuously updates latest_btc_price."""
    global latest_btc_price
    proxy_url, _ = get_aiohttp_connector()

    print("[BTC FEED] Connecting to Binance WebSocket...")
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                ws_kwargs = {"proxy": proxy_url} if proxy_url else {}
                async with session.ws_connect(BINANCE_WS_URL, **ws_kwargs) as ws:
                    print("[BTC FEED] Connected.")
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            price = float(data.get("p", 0))
                            if price > 0:
                                async with _lock:
                                    latest_btc_price = price
                        elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSED):
                            print("[BTC FEED] Connection lost, reconnecting...")
                            break
        except Exception as e:
            print(f"[BTC FEED] Error: {e} — retrying in 3s")
            await asyncio.sleep(3)
