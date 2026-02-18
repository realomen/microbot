from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from models import Trade, SessionLocal
from sqlalchemy import func, desc
from config.settings import settings
import structlog
from datetime import datetime, timedelta

logger = structlog.get_logger()

class TelegramDashboard:
    def __init__(self):
        self.app = Application.builder().token(settings.TELEGRAM_TOKEN).build()
        self._register_handlers()

    def _register_handlers(self):
        self.app.add_handler(CommandHandler("status", self.status))
        self.app.add_handler(CommandHandler("positions", self.positions))
        self.app.add_handler(CommandHandler("report", self.report))
        self.app.add_handler(CommandHandler("trades", self.trades))
        self.app.add_handler(CommandHandler("pause", self.pause))
        self.app.add_handler(CommandHandler("resume", self.resume))

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        with SessionLocal() as db:
            active = db.query(func.count(Trade.id)).filter(Trade.resolved == False).scalar() or 0
            exposure = db.query(func.sum(Trade.amount_usd)).filter(Trade.resolved == False).scalar() or 0
            total_pnl = db.query(func.sum(Trade.pnl)).filter(Trade.resolved == True).scalar() or 0
        text = (
            f"🤖 50/50 MicroBot\n\n"
            f"Активных ставок: {active}\n"
            f"Экспозиция: ${exposure:.1f} / ${settings.MAX_EXPOSURE_USD}\n"
            f"Реализованный PnL: ${total_pnl:.2f}\n"
            f"Режим: {'PAUSED' if settings.PAUSED else 'RUNNING'} | Dry-run: {settings.DRY_RUN}"
        )
        await update.message.reply_text(text)

    async def positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        with SessionLocal() as db:
            trades = db.query(Trade).filter(Trade.resolved == False).order_by(desc(Trade.timestamp)).all()

        if not trades:
            await update.message.reply_text("✅ Нет активных позиций")
            return

        text = "📊 АКТИВНЫЕ ПОЗИЦИИ\n\n"
        for t in trades:
            unrealized = " (unrealized PnL будет в следующей версии)"
            text += f"🔹 {t.question[:60]}{'...' if len(t.question)>60 else ''}\n"
            text += f"   Side: {t.side} | ${t.amount_usd} | Entry: {t.entry_price:.4f} | Shares: {t.shares:.2f}\n"
            text += f"   {unrealized}\n\n"
        await update.message.reply_text(text, parse_mode="Markdown")

    async def report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        with SessionLocal() as db:
            total_trades = db.query(func.count(Trade.id)).scalar() or 0
            resolved = db.query(func.count(Trade.id)).filter(Trade.resolved == True).scalar() or 0
            total_pnl = db.query(func.sum(Trade.pnl)).filter(Trade.resolved == True).scalar() or 0
            wins = db.query(func.count(Trade.id)).filter(Trade.resolved == True, Trade.pnl > 0).scalar() or 0
            win_rate = (wins / resolved * 100) if resolved > 0 else 0

        text = (
            f"📈 ОТЧЁТ ЗА ВСЁ ВРЕМЯ\n\n"
            f"Всего сделок: {total_trades}\n"
            f"Закрыто: {resolved}\n"
            f"Реализованный PnL: ${total_pnl:.2f}\n"
            f"Win-rate: {win_rate:.1f}%\n"
            f"Средняя ставка: ${settings.BET_SIZE_USD}\n"
            f"Макс. экспозиция: ${settings.MAX_EXPOSURE_USD}"
        )
        await update.message.reply_text(text)

    async def trades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        with SessionLocal() as db:
            trades = db.query(Trade).order_by(desc(Trade.timestamp)).limit(15).all()

        if not trades:
            await update.message.reply_text("Нет сделок")
            return

        text = "📜 ПОСЛЕДНИЕ 15 СДЕЛОК\n\n"
        for t in trades:
            status = "✅ CLOSED" if t.resolved else "🔴 OPEN"
            pnl_str = f" PnL: ${t.pnl:.2f}" if t.resolved and t.pnl is not None else ""
            text += f"{t.timestamp.strftime('%d.%m %H:%M')} | {status} | {t.side} ${t.amount_usd} {pnl_str}\n"
        await update.message.reply_text(text)

    async def pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        settings.PAUSED = True
        await update.message.reply_text("⏸ Бот приостановлен (сканер остановлен)")

    async def resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        settings.PAUSED = False
        await update.message.reply_text("▶️ Бот возобновлён")

# Глобальный экземпляр (используется в main.py)
dashboard = TelegramDashboard()
