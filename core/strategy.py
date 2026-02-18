from py_clob_client.order_builder.constants import BUY, SELL
from config.settings import settings
import json
import structlog

logger = structlog.get_logger()

def parse_outcome_prices(market):
    """Максимально надёжный парсинг outcomePrices"""
    raw = market.get("outcomePrices", "[]")
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except:
            return []
    return raw

def decide_side_and_amount(market: dict):
    try:
        outcome_prices = parse_outcome_prices(market)
        if len(outcome_prices) != 2:
            raise ValueError("Invalid outcomePrices")

        p_yes = float(outcome_prices[0])

        idx = 0 if p_yes <= 0.5 else 1
        token_id = market["clobTokenIds"][idx]
        side = BUY if p_yes <= 0.5 else SELL

        amount = min(settings.BET_SIZE_USD, settings.MAX_EXPOSURE_USD * 0.05)

        return token_id, side, amount
    except Exception as e:
        logger.error("decide_side_and_amount failed", question=market.get("question", "")[:60], error=str(e))
        raise
