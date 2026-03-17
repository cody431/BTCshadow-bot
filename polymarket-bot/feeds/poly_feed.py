"""
Polymarket feed — fetches active BTC 5-minute markets and prices
via the Gamma API (gamma-api.polymarket.com).
"""

import httpx
from datetime import datetime, timezone
from config import VERIFY_SSL


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(verify=VERIFY_SSL, timeout=10.0)


async def get_active_btc_markets() -> list[dict]:
    """
    Returns active BTC 5-minute up/down markets from the Gamma API.
    Each dict contains: id, question, close_time, tokens, price_up, price_down
    """
    async with _client() as client:
        resp = await client.get(
            "https://gamma-api.polymarket.com/events",
            params={"active": "true", "limit": "50"}
        )
        resp.raise_for_status()
        events = resp.json()

    markets = []
    for event in events:
        ticker = event.get("ticker", "")
        if "btc-updown-5m" not in ticker:
            continue
        if event.get("closed") or not event.get("active"):
            continue

        for m in event.get("markets", []):
            outcomes = m.get("outcomes", "[]")
            prices = m.get("outcomePrices", "[]")

            # Parse JSON strings if needed
            if isinstance(outcomes, str):
                import json
                outcomes = json.loads(outcomes)
                prices = json.loads(prices)

            price_up = 0.0
            price_down = 0.0
            for i, outcome in enumerate(outcomes):
                if outcome.lower() == "up":
                    price_up = float(prices[i])
                elif outcome.lower() == "down":
                    price_down = float(prices[i])

            markets.append({
                "id": m.get("conditionId"),
                "question": m.get("question"),
                "close_time": m.get("endDate"),
                "tokens": m.get("clobTokenIds", []),
                "price_up": price_up,
                "price_down": price_down,
            })

    return markets


async def get_contract_price(market_id: str, direction: str) -> float:
    """
    Returns the current price for UP or DOWN from the Gamma API.
    """
    async with _client() as client:
        resp = await client.get(
            "https://gamma-api.polymarket.com/markets",
            params={"conditionId": market_id}
        )
        resp.raise_for_status()
        data = resp.json()

    if not data:
        return 0.0

    m = data[0] if isinstance(data, list) else data
    outcomes = m.get("outcomes", "[]")
    prices = m.get("outcomePrices", "[]")

    if isinstance(outcomes, str):
        import json
        outcomes = json.loads(outcomes)
        prices = json.loads(prices)

    for i, outcome in enumerate(outcomes):
        if outcome.lower() == direction.lower():
            return float(prices[i])
    return 0.0


def seconds_to_close(close_time_iso: str) -> float:
    """Returns how many seconds remain until market close."""
    try:
        close_dt = datetime.fromisoformat(close_time_iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return (close_dt - now).total_seconds()
    except Exception:
        return 0.0
