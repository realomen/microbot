import structlog
import asyncio
import os
import nest_asyncio   # ← ОБЯЗАТЕЛЬНО

nest_asyncio.apply()

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
from models import init_db

logger = structlog.get_logger()

init_db()

executor = Executor()
risk = RiskManager()
withdrawer = Withdrawer()

scheduler = BackgroundScheduler()

def scan_and_trade():
    logger.info("=== SCAN JOB STARTED ===")
    try:
        markets = get_active_markets()
        count = potential = bets = 0
        for event in markets:
            for m in event.get("markets", []):
                count += 1
                if is_fifty_fifty_market(m):
                    potential += 1
                    if risk.can_trade(m["id"]):
                        token, side, amount = decide_side_and_amount(m)
                        logger.info("✅ PLACING BET", question=m.get("question","")[:60], side=side, amount=amount)
                        executor.execute(token, side, amount)
                        if not settings.DRY_RUN:
                            entry_price = float(m["outcomePrices"][0 if side == "BUY" else 1])
                            risk.register_trade(m, amount, entry_price, amount / entry_price, side)
                        bets += 1
        logger.info("Scan completed", total_markets=count, potential_50_50=potential, bets_placed=bets)
    except Exception as e:
        logger.error("Scan crashed", error=str(e))

scheduler.add_job(scan_and_trade, IntervalTrigger(minutes=3))  # 3 минуты — удобно для теста
scheduler.add_job(withdrawer.withdraw, IntervalTrigger(hours=6))
scheduler.start()

logger.info("Background scheduler started")

if __name__ == "__main__":
    logger.info("🚀 Polymarket 50/50 MicroBot started", dry_run=settings.DRY_RUN)

    flag = "/tmp/startup_sent.flag"
    if not os.path.exists(flag):
        try:
            async def send_startup():
                bot = Bot(token=settings.TELEGRAM_TOKEN)
                await bot.send_message(
                    chat_id=settings.TELEGRAM_CHAT_ID,
                    text=f"🚀 Бот запущен в тестовом режиме\nСкан каждые 3 минуты | Dry-run: {settings.DRY_RUN}"
                )
            asyncio.run(send_startup())
            open(flag, 'w').close()
        except Exception as e:
            logger.warning("Startup failed", error=str(e))

    # Первый скан сразу
    scan_and_trade()

    dashboard = TelegramDashboard()
    logger.info("Starting Telegram polling...")
    dashboard.app.run_polling(drop_pending_updates=True)
