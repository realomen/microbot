import requests
import json
from typing import List, Dict
from config.settings import settings
import structlog

logger = structlog.get_logger()

GAMMA_URL = "https://gamma-api.polymarket.com"

def get_active_markets() -> List[Dict]:
    resp = requests.get(f"{GAMMA_URL}/events", params={"active": "true", "closed": "false", "limit": 500}, timeout=15)
    resp.raise_for_status()
    return resp.json()

def is_fifty_fifty_market(market: Dict) -> bool:
    try:
        # outcomePrices приходит как строка — парсим
        outcome_str = market.get("outcomePrices", "[]")
        outcome_prices = json.loads(outcome_str)
        if len(outcome_prices) != 2:
            return False

        p0 = float(outcome_prices[0])
        p1 = float(outcome_prices[1])

        # Используем числовые поля (более надёжно)
        liquidity = float(market.get("liquidityNum", market.get("liquidity", 0)))
        volume = float(market.get("volumeNum", market.get("volume", 0)))

        is_50_50 = abs(p0 - 0.5) < settings.PROB_THRESHOLD

        # Детальное логирование для диагностики
        if len(market.get("question", "")) > 0:
            logger.debug("Market checked",
                         question=market["question"][:60],
                         p0=round(p0, 4),
                         p1=round(p1, 4),
                         liquidity=round(liquidity, 0),
                         volume=round(volume, 0),
                         passes_prob=is_50_50)

        return (is_50_50 and
                liquidity >= settings.MIN_LIQUIDITY and
                volume >= settings.MIN_VOLUME)

    except Exception as e:
        logger.warning("Parse error in market", market_id=market.get("id"), error=str(e))
        return False
