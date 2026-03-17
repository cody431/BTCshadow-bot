import csv
import os
from datetime import datetime, timezone
from config import LOG_FILE


HEADERS = [
    "timestamp", "market_id", "direction", "entry_price",
    "target_price", "position_size", "outcome", "pnl", "notes"
]


def _ensure_log_file():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=HEADERS)
            writer.writeheader()


def log_trade(market_id: str, direction: str, entry_price: float,
              target_price: float, position_size: float,
              outcome: str = "OPEN", pnl: float = 0.0, notes: str = ""):
    _ensure_log_file()
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "market_id": market_id,
        "direction": direction,
        "entry_price": entry_price,
        "target_price": target_price,
        "position_size": position_size,
        "outcome": outcome,
        "pnl": pnl,
        "notes": notes,
    }
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writerow(row)
    print(f"[LOG] {row['timestamp']} | {direction} @ {entry_price} | {outcome} | PnL: {pnl}")
