from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from models import Trade, SessionLocal
from sqlalchemy import func, desc
from config.settings import settings
import structlog

logger = structlog.get_logger()

class TelegramDashboard:
    def __init__(self):
        self.app = Application.builder().token(settings.TELEGRAM_TOKEN).build()
        self._register_handlers()
        logger.info("Telegram handlers registered")

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
        await update.message.reply_text(
            f"🤖 50/50 MicroBot\n\n"
            f"Активных ставок: {active}\n"
            f"Экспозиция: ${exposure:.1f} / ${settings.MAX_EXPOSURE_USD}\n"
            f"Реализованный PnL: ${total_pnl:.2f}\n"
            f"Режим: {'PAUSED' if settings.PAUSED else 'RUNNING'}"
        )


    async def positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        with SessionLocal() as db:
            trades = db.query(Trade).filter(Trade.resolved == False).order_by(desc(Trade.timestamp)).all()

        if not trades:
            await update.message.reply_text("✅ Нет активных позиций")
            return

        text = "📊 АКТИВНЫЕ ПОЗИЦИИ + LIVE PnL\n\n"
        for t in trades:
            pos = db.query(Position).filter(Position.market_id == t.market_id).first()
            unreal = f"${pos.unrealized_pnl:+.2f}" if pos and pos.unrealized_pnl is not None else "—"
            curr = f"{pos.current_price:.4f}" if pos and pos.current_price else "—"

            text += f"🔹 {t.question[:60]}{'...' if len(t.question) > 60 else ''}\n"
            text += f"   {t.side} | ${t.amount_usd} | Entry {t.entry_price:.4f} → {curr}\n"
            text += f"   Unrealized PnL: {unreal}\n\n"
        await update.message.reply_text(text)

        with SessionLocal() as db:
            trades = db.query(Trade).filterrade.resolved == False).order_by(desc(Trade.timestamp)).all()
        if not trades:
            await update.message.reply_text("✅ Нет активных позиций")
            return
        text = "📊 АКТИВНЫЕ ПОЗИЦИИ\n\n"
        for t in trades:

    async def report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        with SessionLocal() as db:
            total = db.query(func.count(Trade.id)).scalar() or 0
            resolved = db.query(func.count(Trade.id)).filter(Trade.resolved == True).scalar() or 0
            pnl = db.query(func.sum(Trade.pnl)).filter(Trade.resolved == True).scalar() or 0
        await update.message.reply_text(f"📈 Всего сделок: {total}\nЗакрыто: {resolved}\nPnL: ${pnl:.2f}")

    async def trades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        with SessionLocal() as db:
            trades = db.query(Trade).order_by(desc(Trade.timestamp)).limit(10).all()
        text = "📜 Последние сделки:\n\n"
        for t in trades:
            text += f"{t.timestamp.strftime('%H:%M')} {t.side} ${t.amount_usd} {'✅' if t.resolved else '🔴'}\n"
        await update.message.reply_text(text)

    async def pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        settings.PAUSED = True
        await update.message.reply_text("⏸ Бот приостановлен")

    async def resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        settings.PAUSED = False
        await update.message.reply_text("▶️ Бот запущен")

dashboard = TelegramDashboard()
