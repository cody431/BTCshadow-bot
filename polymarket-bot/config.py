# ============================================================
# POLYMARKET BOT — CONFIGURATION
# Fill in your credentials before running.
# ============================================================

# --- Paper Trading Mode ---
# Set to True to simulate trades without a real wallet or funds.
# All orders are faked — no real money at risk.
PAPER_TRADING = True
PAPER_STARTING_BALANCE = 1000.0   # Simulated USDC starting balance

# --- Ethereum Wallet ---
# Only needed when PAPER_TRADING = False.
# NEVER share your private key or commit it to git.
PRIVATE_KEY = "YOUR_PRIVATE_KEY_HERE"          # e.g. "0xabc123..."
WALLET_ADDRESS = "YOUR_WALLET_ADDRESS_HERE"    # e.g. "0xDEF456..."

# Polymarket uses Polygon network. Fund this wallet with USDC on Polygon.
# Chain ID 137 = Polygon Mainnet
CHAIN_ID = 137

# --- Polymarket API ---
POLYMARKET_HOST = "https://clob.polymarket.com"
# Disable SSL verification if you get certificate errors (e.g. Australia geo-block redirect).
# Safe for paper trading. When going live use a US VPS instead.
VERIFY_SSL = False

# --- Binance WebSocket ---
BINANCE_WS_URL = "wss://stream.binance.com:9443/ws/btcusdt@trade"

# --- Geo-block Proxy (required if running from Australia) ---
# Set USE_PROXY = True and fill in your residential proxy details.
# Recommended: Bright Data, Oxylabs, or Smartproxy (US residential IP).
USE_PROXY = False
PROXY_URL = "http://USERNAME:PASSWORD@us-residential-proxy.example.com:PORT"

# --- Risk Management ---
MAX_POSITION_SIZE = 50      # Max USDC per single trade
MAX_DAILY_LOSS = 200        # Bot shuts down if daily loss reaches this (USDC)
MIN_SECONDS_TO_CLOSE = 10   # Don't enter a trade if less than this many seconds remain
MAX_SECONDS_TO_CLOSE = 90   # Only enter in the final 90-second window
LAG_THRESHOLD = 0.15        # Minimum price lag (in dollars) required to trigger entry
ENTRY_MAX_PRICE = 0.25      # Only buy if contract price is at or below this
TARGET_SELL_PRICE = 0.40    # Limit sell target price

# --- Logging ---
LOG_FILE = "trades.csv"
