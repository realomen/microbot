from models import Trade, SessionLocal
from sqlalchemy import func
from config.settings import settings

class RiskManager:
    def can_trade(self, market_id: str) -> bool:
        with SessionLocal() as db:
            exposure = db.query(func.sum(Trade.amount_usd)).filter(Trade.resolved == False).scalar() or 0.0
            if exposure + settings.BET_SIZE_USD > settings.MAX_EXPOSURE_USD:
                return False
            if db.query(Trade).filter(Trade.market_id == market_id, Trade.resolved == False).first():
                return False
        return True

    def register_trade(self, market: dict, amount: float, entry_price: float, shares: float, side: str):
        with SessionLocal() as db:
            trade = Trade(
                market_id=market["id"],
                token_id=market["clobTokenIds"][0],
                question=market["question"],
                side=side,
                amount_usd=amount,
                entry_price=entry_price,
                shares=shares
            )
            db.add(trade)
            db.commit()
