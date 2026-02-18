from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from models import Trade, SessionLocal
from sqlalchemy import func
from config.settings import settings
import structlog

logger = structlog.get_logger()

class TelegramDashboard:
    def __init__(self):
        self.app = Application.builder().token(settings.TELEGRAM_TOKEN).build()
        self.app.add_handler(CommandHandler("status", self.status))
        self.app.add_handler(CommandHandler("pause", self.pause))
        self.app.add_handler(CommandHandler("resume", self.resume))
        # можно добавить /positions /report позже

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        with SessionLocal() as db:
            active = db.query(func.count(Trade.id)).filter(Trade.resolved == False).scalar()
            exp = db.query(func.sum(Trade.amount_usd)).filter(Trade.resolved == False).scalar() or 0
        await update.message.reply_text(
            f"🤖 50/50 MicroBot\n"
            f"Активно: {active} ставок\n"
            f"Экспозиция: ${exp:.1f}/{settings.MAX_EXPOSURE_USD}\n"
            f"Режим: {'PAUSED' if settings.PAUSED else 'RUNNING'}\n"
            f"Dry-run: {settings.DRY_RUN}"
        )

    async def pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        settings.PAUSED = True
        await update.message.reply_text("⏸ Бот приостановлен")

    async def resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        settings.PAUSED = False
        await update.message.reply_text("▶️ Бот запущен")
