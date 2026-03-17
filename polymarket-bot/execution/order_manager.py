"""
Order execution — places buy/sell orders on Polymarket.
In PAPER_TRADING mode all orders are simulated (no wallet required).
"""

import uuid
from config import (
    PRIVATE_KEY,
    WALLET_ADDRESS,
    CHAIN_ID,
    POLYMARKET_HOST,
    MAX_POSITION_SIZE,
    TARGET_SELL_PRICE,
    PAPER_TRADING,
    PAPER_STARTING_BALANCE,
)
from utils.logger import log_trade

# ── Daily P&L tracking ────────────────────────────────────────────────────────
_daily_pnl: float = 0.0


def get_daily_pnl() -> float:
    return _daily_pnl


def record_pnl(amount: float):
    global _daily_pnl
    _daily_pnl += amount


# ── Paper trading state ───────────────────────────────────────────────────────
_paper_balance: float = PAPER_STARTING_BALANCE
_paper_positions: dict[str, dict] = {}   # order_id -> position info
_paper_trade_count: int = 0


def get_paper_balance() -> float:
    return _paper_balance


def get_paper_summary() -> str:
    pnl = _daily_pnl
    sign = "+" if pnl >= 0 else ""
    return (
        f"  Balance : ${_paper_balance:.2f} USDC\n"
        f"  Daily PnL: {sign}${pnl:.2f}\n"
        f"  Trades  : {_paper_trade_count}"
    )


# ── Live order client (only used when PAPER_TRADING = False) ──────────────────
def _build_client():
    from py_clob_client.client import ClobClient
    return ClobClient(
        host=POLYMARKET_HOST,
        key=PRIVATE_KEY,
        chain_id=CHAIN_ID,
        signature_type=0,
        funder=WALLET_ADDRESS,
    )


# ── Public API ────────────────────────────────────────────────────────────────

async def place_buy_order(
    market_id: str,
    token_id: str,
    direction: str,
    entry_price: float,
    size: float = MAX_POSITION_SIZE,
) -> str | None:
    """
    Places (or simulates) a buy order.
    Returns a fake/real order ID on success, None on failure.
    """
    if PAPER_TRADING:
        return _paper_buy(market_id, token_id, direction, entry_price, size)
    return await _live_buy(market_id, token_id, direction, entry_price, size)


async def place_limit_sell(
    market_id: str,
    token_id: str,
    direction: str,
    num_shares: float,
    sell_price: float = TARGET_SELL_PRICE,
) -> str | None:
    if PAPER_TRADING:
        return _paper_sell(market_id, token_id, direction, num_shares, sell_price)
    return await _live_sell(market_id, token_id, direction, num_shares, sell_price)


# ── Paper trading internals ───────────────────────────────────────────────────

def _paper_buy(market_id, token_id, direction, entry_price, size) -> str | None:
    global _paper_balance, _paper_trade_count

    if _paper_balance < size:
        print(f"[PAPER] Insufficient balance (${_paper_balance:.2f}) for ${size} trade. Skipping.")
        return None

    order_id = f"PAPER-{uuid.uuid4().hex[:8].upper()}"
    num_shares = round(size / entry_price, 4)
    _paper_balance -= size
    _paper_trade_count += 1

    _paper_positions[order_id] = {
        "market_id": market_id,
        "token_id": token_id,
        "direction": direction,
        "entry_price": entry_price,
        "num_shares": num_shares,
        "cost": size,
    }

    print(
        f"[PAPER] BUY  | {direction} | {num_shares} shares @ ${entry_price:.3f} "
        f"| Cost: ${size:.2f} | Balance: ${_paper_balance:.2f} | ID: {order_id}"
    )
    log_trade(
        market_id=market_id,
        direction=direction,
        entry_price=entry_price,
        target_price=TARGET_SELL_PRICE,
        position_size=size,
        outcome="PAPER_OPEN",
        notes=f"order_id={order_id} shares={num_shares}",
    )
    return order_id


def _paper_sell(market_id, token_id, direction, num_shares, sell_price) -> str | None:
    global _paper_balance

    order_id = f"PAPER-SELL-{uuid.uuid4().hex[:8].upper()}"
    proceeds = round(num_shares * sell_price, 4)

    # Find matching buy to calculate P&L
    buy = next(
        (p for p in _paper_positions.values()
         if p["market_id"] == market_id and p["direction"] == direction),
        None,
    )
    cost = buy["cost"] if buy else 0.0
    pnl = round(proceeds - cost, 4)

    _paper_balance += proceeds
    record_pnl(pnl)

    sign = "+" if pnl >= 0 else ""
    print(
        f"[PAPER] SELL | {direction} | {num_shares} shares @ ${sell_price:.3f} "
        f"| Proceeds: ${proceeds:.2f} | PnL: {sign}${pnl:.2f} | Balance: ${_paper_balance:.2f}"
    )
    log_trade(
        market_id=market_id,
        direction=direction,
        entry_price=sell_price,
        target_price=sell_price,
        position_size=proceeds,
        outcome="PAPER_CLOSED",
        pnl=pnl,
        notes=f"order_id={order_id}",
    )
    return order_id


# ── Live order internals ──────────────────────────────────────────────────────

async def _live_buy(market_id, token_id, direction, entry_price, size) -> str | None:
    from py_clob_client.clob_types import OrderArgs
    try:
        client = _build_client()
        num_shares = round(size / entry_price, 4)
        order_args = OrderArgs(token_id=token_id, price=entry_price, size=num_shares, side="BUY")
        resp = client.create_and_post_order(order_args)
        order_id = resp.get("orderID") or resp.get("id")
        print(f"[ORDER] BUY placed | {direction} @ {entry_price} | id={order_id}")
        log_trade(market_id, direction, entry_price, TARGET_SELL_PRICE, size, "OPEN", notes=f"order_id={order_id}")
        return order_id
    except Exception as e:
        print(f"[ORDER] BUY failed: {e}")
        log_trade(market_id, direction, entry_price, TARGET_SELL_PRICE, size, "FAILED", notes=str(e))
        return None


async def _live_sell(market_id, token_id, direction, num_shares, sell_price) -> str | None:
    from py_clob_client.clob_types import OrderArgs
    try:
        client = _build_client()
        order_args = OrderArgs(token_id=token_id, price=sell_price, size=num_shares, side="SELL")
        resp = client.create_and_post_order(order_args)
        order_id = resp.get("orderID") or resp.get("id")
        print(f"[ORDER] LIMIT SELL placed | {sell_price} | id={order_id}")
        return order_id
    except Exception as e:
        print(f"[ORDER] SELL failed: {e}")
        return None
