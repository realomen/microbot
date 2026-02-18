from web3 import Web3
from web3.middleware import geth_poa_middleware
from models import Trade, SessionLocal
from sqlalchemy import func
from config.settings import settings
import structlog
from datetime import datetime, timedelta

logger = structlog.get_logger()

USDC = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
ABI = [{"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},
       {"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},
       {"constant":False,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"type":"function"}]

class Withdrawer:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(settings.POLYGON_RPC_URL))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.account = self.w3.eth.account.from_key(settings.PRIVATE_KEY)
        self.usdc = self.w3.eth.contract(address=USDC, abi=ABI)
        self.last_withdraw = None

    def get_balance(self) -> float:
        return self.usdc.functions.balanceOf(self.account.address).call() / 10**6

    def realized_pnl(self) -> float:
        with SessionLocal() as db:
            return db.query(func.sum(Trade.pnl)).filter(Trade.resolved == True).scalar() or 0.0

    def withdraw(self):
        if self.last_withdraw and (datetime.utcnow() - self.last_withdraw) < timedelta(hours=24):
            return
        profit = self.realized_pnl()
        balance = self.get_balance()
        if profit < settings.WITHDRAW_THRESHOLD or balance < settings.KEEP_IN_HOT + 10:
            return
        amt = min(profit * 0.95, balance - settings.KEEP_IN_HOT)
        if amt < 10:
            return

        tx = self.usdc.functions.transfer(settings.COLD_WALLET, int(amt * 10**6)).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 100000,
            'gasPrice': self.w3.eth.gas_price * 2
        })
        signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        logger.info("AUTO-WITHDRAW", amount=round(amt,2), tx=tx_hash.hex())
        self.last_withdraw = datetime.utcnow()
