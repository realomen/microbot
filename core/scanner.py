import requests
from typing import List, Dict
from config.settings import settings

GAMMA_URL = "https://gamma-api.polymarket.com"

def get_active_markets() -> List[Dict]:
    resp = requests.get(f"{GAMMA_URL}/events", params={"active": "true", "closed": "false", "limit": 500}, timeout=15)
    resp.raise_for_status()
    return resp.json()

def is_fifty_fifty_market(market: Dict) -> bool:
    if len(market.get("outcomePrices", [])) != 2:
        return False
    try:
        p0 = float(market["outcomePrices"][0])
        liquidity = float(market.get("liquidity", 0))
        volume = float(market.get("volume", 0))
        return (abs(p0 - 0.5) < settings.PROB_THRESHOLD and
                liquidity >= settings.MIN_LIQUIDITY and
                volume >= settings.MIN_VOLUME)
    except:
        return False
