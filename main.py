import structlog
import asyncio
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from telegram import Bot

from config.settings import settings
from core.scanner import get_active_markets, is_fifty_fifty_market
from core.strategy import decide_side_and_amount
from core.executor import Executor
from core.risk import RiskManager
from core.withdrawer import Withdrawer
from core.telegram_dashboard import TelegramDashboard
from models import init_db   # ← новый импорт

logger = structlog.get_logger()

# Инициализируем БД с ожиданием Postgres
init_db()

executor = Executor()
risk = RiskManager()
withdrawer = Withdrawer()

scheduler = BackgroundScheduler()

def scan_and_trade():
    if settings.PAUSED:
        return
    try:
        markets = get_active_markets()
        count = 0
        for event in markets:
            for m in event.get("markets", []):
                if is_fifty_fifty_market(m):
                    if risk.can_trade(m["id"]):
                        token, side, amount = decide_side_and_amount(m)
                        executor.execute(token, side, amount)
                        if not settings.DRY_RUN:
                            entry_price = float(m["outcomePrices"][0 if side == "BUY" else 1])
                            risk.register_trade(m, amount, entry_price, amount / entry_price, side)
                        count += 1
        logger.info("Scan completed", markets_scanned=count)
    except Exception as e:
        logger.error("Scan error", error=str(e))

scheduler.add_job(scan_and_trade, IntervalTrigger(minutes=12))
scheduler.add_job(withdrawer.withdraw, IntervalTrigger(hours=6))
scheduler.start()
logger.info("Background scheduler started")

if __name__ == "__main__":
    logger.info("🚀 Polymarket 50/50 MicroBot started", dry_run=settings.DRY_RUN)

    # Защита от спама + правильный asyncio
    flag = "/tmp/startup_sent.flag"
    if not os.path.exists(flag):
        try:
            async def send_startup():
                bot = Bot(token=settings.TELEGRAM_TOKEN)
                await bot.send_message(
                    chat_id=settings.TELEGRAM_CHAT_ID,
                    text=f"🚀 Polymarket 50/50 MicroBot запущен успешно!\n"
                         f"Режим: {'DRY-RUN' if settings.DRY_RUN else 'LIVE'} | "
                         f"Экспозиция: ${settings.MAX_EXPOSURE_USD}"
                )
            asyncio.run(send_startup())
            open(flag, 'w').close()
        except Exception as e:
            logger.warning("Startup message failed", error=str(e))

    dashboard = TelegramDashboard()
    logger.info("Starting Telegram polling...")
    dashboard.app.run_polling(drop_pending_updates=True)
