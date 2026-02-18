import requests
from models import Trade, Position, SessionLocal
from sqlalchemy import func
from config.settings import settings
import structlog
from datetime import datetime

logger = structlog.get_logger()

class Resolver:
    def check_resolved(self):
        with SessionLocal() as db:
            open_trades = db.query(Trade).filter(Trade.resolved == False).all()
            for t in open_trades:
                try:
                    r = requests.get(f"https://gamma-api.polymarket.com/markets/{t.market_id}", timeout=10)
                    if r.status_code != 200:
                        continue
                    data = r.json()
                    if data.get("closed") or data.get("resolved"):
                        winner = int(data.get("winner", -1))  # 0 или 1
                        final_price = 1.0 if (winner == 0 and t.side == "BUY") or (winner == 1 and t.side == "SELL") else 0.0
                        pnl = (final_price - t.entry_price) * t.shares if t.side == "BUY" else (t.entry_price - final_price) * t.shares

                        t.resolved = True
                        t.resolution_price = final_price
                        t.pnl = pnl

                        # закрываем Position
                        pos = db.query(Position).filter(Position.market_id == t.market_id).first()
                        if pos:
                            pos.current_price = final_price
                            pos.unrealized_pnl = pnl

                        logger.info("Market resolved", question=t.question[:50], pnl=round(pnl, 2))
                except Exception as e:
                    logger.warning("Resolution check failed", market=t.market_id, error=str(e))
            db.commit()

resolver = Resolver()
