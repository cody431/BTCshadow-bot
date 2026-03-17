"""
Polymarket feed — fetches active BTC 5-minute markets, order book prices,
and market close times via the CLOB REST API.
"""

import asyncio
import httpx
from datetime import datetime, timezone
from config import POLYMARKET_HOST, VERIFY_SSL
from utils.proxy import get_proxy_config


def _client() -> httpx.AsyncClient:
    proxy_config = get_proxy_config()
    # httpx 0.20+ uses 'proxy' (single string) instead of 'proxies' (dict)
    if proxy_config:
        proxy_url = list(proxy_config.values())[0]
        return httpx.AsyncClient(proxy=proxy_url, verify=VERIFY_SSL, timeout=10.0)
    return httpx.AsyncClient(verify=VERIFY_SSL, timeout=10.0)


async def get_active_btc_markets() -> list[dict]:
    """
    Returns a list of active Polymarket markets matching BTC 5-minute format.
    Each market dict contains: id, question, close_time, tokens (UP/DOWN).
    """
    async with _client() as client:
        resp = await client.get(f"{POLYMARKET_HOST}/markets", params={"active": "true"})
        resp.raise_for_status()
        markets = resp.json().get("data", [])

    btc_markets = []
    for m in markets:
        question = m.get("question", "").lower()
        if "btc" in question and ("up or down" in question or "5 minute" in question or "5min" in question):
            btc_markets.append({
                "id": m["condition_id"],
                "question": m["question"],
                "close_time": m.get("end_date_iso") or m.get("close_time"),
                "tokens": m.get("tokens", []),
            })
    return btc_markets


async def get_contract_price(market_id: str, direction: str) -> float:
    """
    Returns the best ask price for the UP or DOWN token in a given market.
    direction: "UP" or "DOWN"
    """
    async with _client() as client:
        resp = await client.get(f"{POLYMARKET_HOST}/orderbook/{market_id}")
        resp.raise_for_status()
        book = resp.json()

    # The order book has bids/asks per token. We want the best ask (cheapest to buy).
    token_id = _get_token_id(book, direction)
    if not token_id:
        return 0.0

    asks = book.get("asks", {}).get(token_id, [])
    if not asks:
        return 0.0
    # asks are sorted ascending by price
    return float(asks[0]["price"])


def _get_token_id(book: dict, direction: str) -> str | None:
    """Finds the token ID for UP or DOWN direction from the order book metadata."""
    for token in book.get("tokens", []):
        outcome = token.get("outcome", "").upper()
        if direction.upper() in outcome:
            return token.get("token_id")
    return None


def seconds_to_close(close_time_iso: str) -> float:
    """Returns how many seconds remain until market close."""
    try:
        close_dt = datetime.fromisoformat(close_time_iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return (close_dt - now).total_seconds()
    except Exception:
        return 0.0
