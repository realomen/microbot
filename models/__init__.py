from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Enum
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
import enum
from config.settings import settings

Base = declarative_base()

class Side(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True)
    market_id = Column(String, nullable=False, index=True)
    token_id = Column(String, nullable=False)
    question = Column(String, nullable=False)
    side = Column(Enum(Side), nullable=False)
    amount_usd = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    shares = Column(Float, nullable=False)
    timestamp = Column(DateTime, server_default=func.now(), index=True)
    resolved = Column(Boolean, default=False)
    resolution_price = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)

class Position(Base):
    __tablename__ = "positions"
    id = Column(Integer, primary_key=True)
    market_id = Column(String, unique=True, index=True)
    token_id = Column(String, nullable=False)
    question = Column(String)
    side = Column(Enum(Side))
    shares = Column(Float)
    entry_avg_price = Column(Float)
    current_price = Column(Float)
    unrealized_pnl = Column(Float, default=0.0)
    last_update = Column(DateTime, server_default=func.now())

engine = create_engine(f"postgresql+psycopg2://bot:{settings.POSTGRES_PASSWORD}@postgres:5432/polymarket_bot")
SessionLocal = sessionmaker(bind=engine)

Base.metadata.create_all(bind=engine)  # для первого запуска
