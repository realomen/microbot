import streamlit as st
import pandas as pd
from datetime import datetime

# === Наши настройки ===
from config.settings import settings
from models import Trade, Position, SessionLocal
from sqlalchemy import func, desc

st.set_page_config(page_title="50/50 MicroBot", layout="wide", page_icon="🤖")
st.title("🤖 Polymarket 50/50 MicroBot")
st.caption("Production v1.0 • Live PnL + Auto-withdraw • Finance-grade")

# Метрики
col1, col2, col3, col4 = st.columns(4)
with SessionLocal() as db:
    active = db.query(func.count(Trade.id)).filter(Trade.resolved == False).scalar() or 0
    exposure = db.query(func.sum(Trade.amount_usd)).filter(Trade.resolved == False).scalar() or 0.0
    total_pnl = db.query(func.sum(Trade.pnl)).filter(Trade.resolved == True).scalar() or 0.0
    wins = db.query(func.count(Trade.id)).filter(Trade.resolved == True, Trade.pnl > 0).scalar() or 0
    resolved_count = db.query(func.count(Trade.id)).filter(Trade.resolved == True).scalar() or 1
    win_rate = round(wins / resolved_count * 100, 1)

col1.metric("Активных ставок", active)
col2.metric("Экспозиция", f"${exposure:.1f}")
col3.metric("Реализованный PnL", f"${total_pnl:.2f}", delta=f"{total_pnl:+.2f}")
col4.metric("Win-rate", f"{win_rate}%")

# График кумулятивного PnL
with SessionLocal() as db:
    trades = db.query(Trade).order_by(Trade.timestamp).all()

if trades:
    cum_pnl = 0
    data = []
    for t in trades:
        cum_pnl += t.pnl or 0
        data.append({
            "date": t.timestamp,
            "pnl": t.pnl or 0,
            "cum_pnl": cum_pnl
        })
    df = pd.DataFrame(data)
    st.subheader("📈 Кумулятивный PnL")
    st.line_chart(df.set_index("date")["cum_pnl"], use_container_width=True)
else:
    st.info("📊 Пока нет закрытых сделок. График появится после первых resolution.")

# Открытые позиции
st.subheader("🔴 Открытые позиции + Live PnL")
with SessionLocal() as db:
    open_pos = db.query(Trade, Position)\
        .join(Position, Trade.market_id == Position.market_id, isouter=True)\
        .filter(Trade.resolved == False)\
        .order_by(desc(Trade.timestamp)).all()

if open_pos:
    data = []
    for t, p in open_pos:
        unreal = f"${p.unrealized_pnl:+.2f}" if p and p.unrealized_pnl is not None else "—"
        curr = f"{p.current_price:.4f}" if p and p.current_price else "—"
        data.append({
            "Вопрос": t.question[:75] + ("..." if len(t.question) > 75 else ""),
            "Side": t.side,
            "Сумма": f"${t.amount_usd}",
            "Entry": f"{t.entry_price:.4f}",
            "Current": curr,
            "Unreal PnL": unreal
        })
    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
else:
    st.success("✅ Все позиции закрыты или ещё не открыты.")

# Нижняя строка
st.caption(
    f"Последнее обновление: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} | "
    f"Dry-run: {settings.DRY_RUN} | "
    f"Экспозиция лимит: ${settings.MAX_EXPOSURE_USD}"
)
