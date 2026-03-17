"""
Core strategy — detects when a Polymarket contract price lags
behind BTC's actual direction and signals a trade entry.
"""

from config import (
    LAG_THRESHOLD,
    ENTRY_MAX_PRICE,
    MIN_SECONDS_TO_CLOSE,
    MAX_SECONDS_TO_CLOSE,
)

# Tracks the BTC price at the open of each market cycle.
# Key: market_id, Value: btc price at market open
_market_open_prices: dict[str, float] = {}


def record_market_open(market_id: str, btc_price: float):
    """Call this when a new market cycle begins to record the opening BTC price."""
    _market_open_prices[market_id] = btc_price
    print(f"[STRATEGY] Market {market_id} opened with BTC @ {btc_price:.2f}")


def detect_lag(
    market_id: str,
    current_btc: float,
    contract_price_up: float,
    contract_price_down: float,
    seconds_remaining: float,
) -> dict | None:
    """
    Checks for a lag signal. Returns a signal dict if a trade should fire,
    or None if no entry conditions are met.

    Signal dict: {"direction": "UP"|"DOWN", "contract_price": float, "fair_value": float}
    """
    # Must be within the entry window
    if not (MIN_SECONDS_TO_CLOSE <= seconds_remaining <= MAX_SECONDS_TO_CLOSE):
        return None

    open_price = _market_open_prices.get(market_id)
    if open_price is None or open_price == 0:
        return None

    btc_direction = "UP" if current_btc > open_price else "DOWN"

    if btc_direction == "UP":
        contract_price = contract_price_up
        # If BTC is clearly up, the "UP" contract fair value should be near 1.0.
        # A conservative fair value estimate: 0.80 when BTC is trending up.
        fair_value = 0.80
    else:
        contract_price = contract_price_down
        fair_value = 0.80

    lag = fair_value - contract_price

    print(
        f"[STRATEGY] {market_id} | BTC {btc_direction} | "
        f"contract={contract_price:.3f} fair={fair_value:.2f} lag={lag:.3f} "
        f"secs_left={seconds_remaining:.1f}"
    )

    if lag >= LAG_THRESHOLD and contract_price <= ENTRY_MAX_PRICE:
        return {
            "direction": btc_direction,
            "contract_price": contract_price,
            "fair_value": fair_value,
            "lag": lag,
        }

    return None
