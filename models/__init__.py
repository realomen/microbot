from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Enum
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
import enum
import time
from config.settings import settings
import structlog

logger = structlog.get_logger()

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

engine = create_engine(
    f"postgresql+psycopg2://bot:{settings.POSTGRES_PASSWORD}@postgres:5432/polymarket_bot",
    pool_pre_ping=True,          # авто-проверка соединения
    pool_recycle=300
)
SessionLocal = sessionmaker(bind=engine)

def init_db(retries=15, delay=2):
    for i in range(retries):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created successfully")
            return
        except Exception as e:
            logger.warning(f"DB not ready yet (attempt {i+1}/{retries})", error=str(e))
            time.sleep(delay)
    raise Exception("Failed to connect to Postgres after retries")

# НЕ вызываем create_all при импорте — только когда нужно
