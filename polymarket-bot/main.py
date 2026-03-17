"""
Polymarket 5-Minute BTC Trading Bot
Entry point — runs all async tasks concurrently.
"""

import asyncio
from datetime import datetime, timezone

from config import MAX_DAILY_LOSS, MAX_POSITION_SIZE, PAPER_TRADING
from feeds.btc_feed import run_btc_feed, get_btc_price
from feeds.poly_feed import get_active_btc_markets, get_contract_price, seconds_to_close
from strategy.lag_detector import detect_lag, record_market_open
from execution.order_manager import place_buy_order, place_limit_sell, get_daily_pnl, get_paper_summary

# Track which markets we've already entered this cycle to avoid double-entry
_entered_markets: set[str] = set()
# Track market open BTC prices
_market_open_btc: dict[str, float] = {}


async def trading_loop():
    """Main loop — scans active markets every 5 seconds and fires trades on signals."""
    print("[BOT] Trading loop started.")

    while True:
        # --- Safety: check daily loss limit ---
        if get_daily_pnl() <= -MAX_DAILY_LOSS:
            print(f"[BOT] Daily loss limit hit (${MAX_DAILY_LOSS}). Shutting down.")
            return

        current_btc = await get_btc_price()
        if current_btc == 0:
            print("[BOT] Waiting for BTC price feed...")
            await asyncio.sleep(2)
            continue

        try:
            markets = await get_active_btc_markets()
        except Exception as e:
            print(f"[BOT] Failed to fetch markets: {e}")
            await asyncio.sleep(5)
            continue

        for market in markets:
            market_id = market["id"]
            close_time = market["close_time"]

            if not close_time:
                continue

            secs_left = seconds_to_close(close_time)

            # Record BTC price at market open (first time we see this market)
            if market_id not in _market_open_btc:
                _market_open_btc[market_id] = current_btc
                record_market_open(market_id, current_btc)

            # Skip markets we've already traded this cycle
            if market_id in _entered_markets:
                continue

            # Fetch current contract prices
            try:
                price_up = await get_contract_price(market_id, "UP")
                price_down = await get_contract_price(market_id, "DOWN")
            except Exception as e:
                print(f"[BOT] Failed to fetch prices for {market_id}: {e}")
                continue

            # Run lag detection
            signal = detect_lag(
                market_id=market_id,
                current_btc=current_btc,
                contract_price_up=price_up,
                contract_price_down=price_down,
                seconds_remaining=secs_left,
            )

            if signal:
                direction = signal["direction"]
                entry_price = signal["contract_price"]

                print(f"[BOT] SIGNAL! {direction} on {market_id} | lag={signal['lag']:.3f} | {secs_left:.1f}s left")

                # Find the token ID for the direction
                token_id = _find_token_id(market["tokens"], direction)
                if not token_id:
                    print(f"[BOT] Could not find token ID for {direction} in {market_id}")
                    continue

                # Fire buy
                order_id = await place_buy_order(
                    market_id=market_id,
                    token_id=token_id,
                    direction=direction,
                    entry_price=entry_price,
                    size=MAX_POSITION_SIZE,
                )

                if order_id:
                    _entered_markets.add(market_id)
                    # Place limit sell immediately after buy
                    num_shares = round(MAX_POSITION_SIZE / entry_price, 4)
                    await place_limit_sell(
                        market_id=market_id,
                        token_id=token_id,
                        direction=direction,
                        num_shares=num_shares,
                    )

        # Clean up markets that have closed
        _cleanup_closed_markets(markets)

        await asyncio.sleep(5)


def _find_token_id(tokens: list[dict], direction: str) -> str | None:
    for token in tokens:
        outcome = token.get("outcome", "").upper()
        if direction.upper() in outcome:
            return token.get("token_id")
    return None


def _cleanup_closed_markets(active_markets: list[dict]):
    """Remove closed markets from tracking sets so they don't accumulate."""
    active_ids = {m["id"] for m in active_markets}
    closed = _entered_markets - active_ids
    for mid in closed:
        _entered_markets.discard(mid)
        _market_open_btc.pop(mid, None)


async def dashboard_loop():
    """Prints a live status summary every 30 seconds."""
    while True:
        await asyncio.sleep(30)
        btc = await get_btc_price()
        print("\n" + "─" * 40)
        print(f"  BTC  : ${btc:,.2f}")
        if PAPER_TRADING:
            print(get_paper_summary())
        else:
            pnl = get_daily_pnl()
            sign = "+" if pnl >= 0 else ""
            print(f"  Daily PnL: {sign}${pnl:.2f}")
        print("─" * 40 + "\n")


async def main():
    mode = "PAPER TRADING (no real money)" if PAPER_TRADING else "LIVE TRADING"
    print("=" * 50)
    print(f"  Polymarket BTC 5-Min Bot — {mode}")
    print(f"  {datetime.now(timezone.utc).isoformat()}")
    print("=" * 50)

    # Run BTC feed, trading loop, and dashboard concurrently
    await asyncio.gather(
        run_btc_feed(),
        trading_loop(),
        dashboard_loop(),
    )


if __name__ == "__main__":
    asyncio.run(main())
