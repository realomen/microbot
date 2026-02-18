import structlog
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from config.settings import settings
from core.scanner import get_active_markets, is_fifty_fifty_market
from core.strategy import decide_side_and_amount
from core.executor import Executor
from core.risk import RiskManager
from core.withdrawer import Withdrawer
from core.telegram_dashboard import TelegramDashboard
from models import Trade, SessionLocal
import threading

logger = structlog.get_logger()
executor = Executor()
risk = RiskManager()
withdrawer = Withdrawer()
scheduler = BlockingScheduler()

def scan_and_trade():
    if settings.PAUSED:
        return
    markets = get_active_markets()
    for event in markets:
        for m in event.get("markets", []):
            if is_fifty_fifty_market(m):
                if risk.can_trade(m["id"]):
                    token, side, amount = decide_side_and_amount(m)
                    resp = executor.execute(token, side, amount)
                    if not settings.DRY_RUN:
                        entry_price = float(m["outcomePrices"][0 if side == "BUY" else 1])
                        risk.register_trade(m, amount, entry_price, amount / entry_price, side)

@scheduler.scheduled_job(IntervalTrigger(minutes=12))
def job_scan():
    scan_and_trade()

@scheduler.scheduled_job(IntervalTrigger(hours=6))
def job_withdraw():
    if not settings.DRY_RUN:
        withdrawer.withdraw()

if __name__ == "__main__":
    logger.info("🚀 Polymarket 50/50 MicroBot started", dry_run=settings.DRY_RUN)

    # Telegram в отдельном потоке
    dashboard = TelegramDashboard()
    threading.Thread(target=dashboard.app.run_polling, daemon=True).start()

    scheduler.start()
