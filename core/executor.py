from py_clob_client.client import ClobClient
from py_clob_client.clob_types import MarketOrderArgs, OrderType
from config.settings import settings
import structlog

logger = structlog.get_logger()

class Executor:
    def __init__(self):
        self.client = ClobClient(
            host="https://clob.polymarket.com",
            key=settings.PRIVATE_KEY,
            chain_id=137,
            funder=settings.FUNDER_ADDRESS,
            signature_type=0
        )
        self.client.set_api_creds(self.client.create_or_derive_api_creds())

    def execute(self, token_id: str, side: str, amount: float):
        if settings.DRY_RUN:
            logger.info("DRY-RUN bet", amount=amount, token=token_id[:8])
            return {"status": "dry_run"}

        mo = MarketOrderArgs(token_id=token_id, amount=amount, side=side, order_type=OrderType.FOK)
        signed = self.client.create_market_order(mo)
        resp = self.client.post_order(signed, OrderType.FOK)
        logger.info("Bet executed", tx=resp)
        return resp
