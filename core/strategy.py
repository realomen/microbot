from py_clob_client.order_builder.constants import BUY, SELL
from config.settings import settings
import json
import structlog

logger = structlog.get_logger()

def parse_outcome_prices(market):
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
            raise ValueError(f"Invalid outcomePrices length: {len(outcome_prices)}")

        p_yes = float(outcome_prices[0])

        clob_token_ids = market.get("clobTokenIds", [])
        if len(clob_token_ids) != 2:
            logger.warning("clobTokenIds not found or invalid", keys=list(market.keys()))
            raise ValueError("No valid clobTokenIds")

        idx = 0 if p_yes <= 0.5 else 1
        token_id = str(clob_token_ids[idx])   # обязательно строка

        side = BUY if p_yes <= 0.5 else SELL
        amount = min(settings.BET_SIZE_USD, settings.MAX_EXPOSURE_USD * 0.05)

        logger.info("✅ Preparing bet",
                    question=market.get("question", "")[:65],
                    p_yes=round(p_yes,4),
                    side=side,
                    token_id=token_id[:16]+"...",
                    amount=amount)

        return token_id, side, amount
    except Exception as e:
        logger.error("decide_side_and_amount failed", question=market.get("question", "")[:50], error=str(e))
        raise
