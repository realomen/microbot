from py_clob_client.order_builder.constants import BUY, SELL
from config.settings import settings

def decide_side_and_amount(market: dict):
    p_yes = float(market["outcomePrices"][0])
    idx = 0 if p_yes <= 0.5 else 1
    token_id = market["clobTokenIds"][idx]
    side = BUY if p_yes <= 0.5 else SELL
    amount = min(settings.BET_SIZE_USD, settings.MAX_EXPOSURE_USD * 0.05)
    return token_id, side, amount
