from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PRIVATE_KEY: str
    FUNDER_ADDRESS: str
    COLD_WALLET: str
    WITHDRAW_THRESHOLD: float = 50.0
    KEEP_IN_HOT: float = 80.0

    POSTGRES_PASSWORD: str

    TELEGRAM_TOKEN: str
    TELEGRAM_CHAT_ID: str

    POLYGON_RPC_URL: str = "https://polygon-rpc.com"

    DRY_RUN: bool = False
    MAX_EXPOSURE_USD: float = 300.0
    BET_SIZE_USD: float = 5.0
    PROB_THRESHOLD: float = 0.07
    MIN_LIQUIDITY: float = 8000.0
    MIN_VOLUME: float = 15000.0
    PAUSED: bool = False

settings = Settings()
