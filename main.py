import structlog
import asyncio
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

logger = structlog.get_logger()

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
                        resp = executor.execute(token, side, amount)
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

    # Правильная отправка startup сообщения (asyncio.run)
    try:
        async def send_startup():
            bot = Bot(token=settings.TELEGRAM_TOKEN)
            await bot.send_message(
                chat_id=settings.TELEGRAM_CHAT_ID,
                text=f"🚀 Polymarket 50/50 MicroBot запущен успешно!\n"
                     f"Режим: {'DRY-RUN' if settings.DRY_RUN else 'LIVE TRADING'}\n"
                     f"Экспозиция: ${settings.MAX_EXPOSURE_USD} | Ставка: ${settings.BET_SIZE_USD}"
            )
        asyncio.run(send_startup())
        logger.info("Startup message sent to Telegram")
    except Exception as e:
        logger.warning("Startup message failed (check chat_id)", error=str(e))

    # Telegram polling в ГЛАВНОМ потоке — всё стабильно
    dashboard = TelegramDashboard()
    logger.info("Starting Telegram polling...")
    dashboard.app.run_polling(drop_pending_updates=True)
