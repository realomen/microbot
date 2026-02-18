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
        # Robust парсинг outcomePrices (может быть строкой или списком)
        outcome_raw = market.get("outcomePrices", "[]")
        if isinstance(outcome_raw, str):
            try:
                outcome_prices = json.loads(outcome_raw)
            except:
                outcome_prices = []
        else:
            outcome_prices = outcome_raw

        if len(outcome_prices) != 2:
            return False

        p0 = float(outcome_prices[0])
        p1 = float(outcome_prices[1])

        liquidity = float(market.get("liquidityNum") or market.get("liquidity", 0))
        volume = float(market.get("volumeNum") or market.get("volume", 0))

        is_50_50 = abs(p0 - 0.5) < settings.PROB_THRESHOLD

        # Детальное логирование (только рынки, близкие к 50/50)
        if abs(p0 - 0.5) < 0.12:  # показываем только близкие к 50/50
            logger.info("Market checked",
                        question=market.get("question", "")[:70],
                        p_yes=round(p0, 4),
                        liquidity=round(liquidity, 0),
                        volume=round(volume, 0),
                        passes=is_50_50 and liquidity >= settings.MIN_LIQUIDITY and volume >= settings.MIN_VOLUME)

        return (is_50_50 and
                liquidity >= settings.MIN_LIQUIDITY and
                volume >= settings.MIN_VOLUME)

    except Exception as e:
        # Один плохой рынок НЕ ломает весь скан
        logger.debug("Market skipped (parse error)", market_id=market.get("id"), error=str(e))
        return False
