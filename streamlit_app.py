import streamlit as st
import pandas as pd
from datetime import datetime
from models import Trade, Position, SessionLocal
from sqlalchemy import func, desc

st.set_page_config(page_title="50/50 MicroBot", layout="wide")
st.title("🤖 Polymarket 50/50 MicroBot Dashboard")
st.caption("Production v1.0 — alex.demichev")

col1, col2, col3, col4 = st.columns(4)
with SessionLocal() as db:
    active = db.query(func.count(Trade.id)).filter(Trade.resolved == False).scalar() or 0
    exposure = db.query(func.sum(Trade.amount_usd)).filter(Trade.resolved == False).scalar() or 0
    total_pnl = db.query(func.sum(Trade.pnl)).filter(Trade.resolved == True).scalar() or 0
    win_rate = round((db.query(func.count(Trade.id)).filter(Trade.resolved == True, Trade.pnl > 0).scalar() or 0) / (db.query(func.count(Trade.id)).filter(Trade.resolved == True).scalar() or 1) * 100, 1)

col1.metric("Активных ставок", active)
col2.metric("Экспозиция", f"${exposure:.1f}")
col3.metric("Реализованный PnL", f"${total_pnl:.2f}")
col4.metric("Win-rate", f"{win_rate}%")

# График PnL
with SessionLocal() as db:
    trades = db.query(Trade).order_by(Trade.timestamp).all()
df = pd.DataFrame([{
    "date": t.timestamp,
    "pnl": t.pnl or 0,
    "cum_pnl": sum(t.pnl or 0 for t in trades[:i+1])
} for i, t in enumerate(trades)])

st.line_chart(df.set_index("date")["cum_pnl"], use_container_width=True)

# Таблица позиций
st.subheader("Открытые позиции + Live PnL")
with SessionLocal() as db:
    open_pos = db.query(Trade, Position).join(Position, Trade.market_id == Position.market_id, isouter=True)\
        .filter(Trade.resolved == False).all()
data = []
for t, p in open_pos:
    data.append({
        "Вопрос": t.question[:70] + "..." if len(t.question) > 70 else t.question,
        "Side": t.side,
        "Amount": f"${t.amount_usd}",
        "Entry": f"{t.entry_price:.4f}",
        "Current": f"{p.current_price:.4f}" if p else "—",
        "Unreal PnL": f"${p.unrealized_pnl:+.2f}" if p else "—"
    })
st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

st.success("✅ Бот работает стабильно | Последнее обновление: " + datetime.now().strftime("%H:%M:%S"))
