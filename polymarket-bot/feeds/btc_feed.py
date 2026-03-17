import asyncio
import json
import aiohttp

latest_btc_price: float = 0.0
_lock = asyncio.Lock()


async def get_btc_price():
    async with _lock:
        return latest_btc_price


async def run_btc_feed():
    global latest_btc_price
    url = "wss://ws.kraken.com"
    sub = json.dumps({
        "event": "subscribe",
        "pair": ["XBT/USD"],
        "subscription": {"name": "ticker"}
    })
    print("[BTC FEED] Connecting to Kraken...")
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(url) as ws:
                    await ws.send_str(sub)
                    print("[BTC FEED] Connected.")
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            if isinstance(data, list) and len(data) > 1:
                                price = float(data[1].get("c", [0])[0])
                                if price > 0:
                                    async with _lock:
                                        latest_btc_price = price
                        elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSED):
                            break
        except Exception as e:
            print(f"[BTC FEED] Error: {e} - retrying in 3s")
            await asyncio.sleep(3)
