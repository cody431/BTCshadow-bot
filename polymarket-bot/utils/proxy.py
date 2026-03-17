from config import USE_PROXY, PROXY_URL


def get_proxy_config() -> dict | None:
    """
    Returns a proxy config dict for httpx/requests, or None if proxy is disabled.
    Use a US-based residential proxy to bypass Australia geo-block.
    """
    if not USE_PROXY:
        return None
    return {
        "http://": PROXY_URL,
        "https://": PROXY_URL,
    }


def get_aiohttp_connector():
    """
    Returns an aiohttp connector with proxy support for WebSocket connections.
    """
    if not USE_PROXY:
        return None, None
    # aiohttp passes proxy as a string to session.ws_connect()
    return PROXY_URL, {"ssl": False}
