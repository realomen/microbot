import structlog
import threading
import asyncio
import nest_asyncio
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

# === Фикс asyncio для Telegram v21+ ===
nest_asyncio.apply()

logger = structlog.get_logger()

executor = Executor()
risk = RiskManager()
withdrawer = Withdrawer()
scheduler = BlockingScheduler()

def scan_and_trade():
    if settings.PAUSED:
        return
    try:
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
    except Exception as e:
        logger.error("Scan error", error=str(e))

@scheduler.scheduled_job(IntervalTrigger(minutes=12))
def job_scan():
    scan_and_trade()

@scheduler.scheduled_job(IntervalTrigger(hours=6))
def job_withdraw():
    if not settings.DRY_RUN:
        withdrawer.withdraw()

# === Правильный запуск Telegram с event loop ===
def start_telegram():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        dashboard = TelegramDashboard()
        logger.info("Telegram polling started")

        # Отправляем стартовое сообщение сразу после запуска
        async def send_startup():
            try:
                await dashboard.app.bot.send_message(
                    chat_id=settings.TELEGRAM_CHAT_ID,
                    text="🚀 Polymarket 50/50 MicroBot успешно запущен!\n"
                         f"Dry-run: {settings.DRY_RUN}\n"
                         f"Экспозиция: ${settings.MAX_EXPOSURE_USD}"
                )
            except Exception as e:
                logger.warning("Cannot send startup message", error=str(e))

        loop.run_until_complete(send_startup())
        loop.run_until_complete(dashboard.app.run_polling())

    except Exception as e:
        logger.error("Telegram thread crashed", error=str(e))

if __name__ == "__main__":
    logger.info("🚀 Polymarket 50/50 MicroBot started", dry_run=settings.DRY_RUN)

    # Telegram в отдельном потоке с правильным loop
    telegram_thread = threading.Thread(target=start_telegram, daemon=True)
    telegram_thread.start()

    # Планировщик в главном потоке (блокирует, но это нормально)
    scheduler.start()
