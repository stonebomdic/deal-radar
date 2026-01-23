from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.config import get_settings
from src.db.database import Base
from src.models import Bank

settings = get_settings()
sync_database_url = settings.database_url.replace("+aiosqlite", "")

BANKS = [
    {"name": "中國信託", "code": "ctbc", "website": "https://www.ctbcbank.com"},
    {"name": "國泰世華", "code": "cathay", "website": "https://www.cathaybk.com.tw"},
    {"name": "玉山銀行", "code": "esun", "website": "https://www.esunbank.com.tw"},
    {"name": "台新銀行", "code": "taishin", "website": "https://www.taishinbank.com.tw"},
    {"name": "富邦銀行", "code": "fubon", "website": "https://www.fubon.com"},
    {"name": "永豐銀行", "code": "sinopac", "website": "https://www.sinopac.com"},
    {"name": "聯邦銀行", "code": "ubot", "website": "https://www.ubot.com.tw"},
    {"name": "第一銀行", "code": "firstbank", "website": "https://www.firstbank.com.tw"},
    {"name": "華南銀行", "code": "hncb", "website": "https://www.hncb.com.tw"},
    {"name": "兆豐銀行", "code": "megabank", "website": "https://www.megabank.com.tw"},
]


def seed_banks():
    """建立銀行種子資料"""
    engine = create_engine(sync_database_url)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        for bank_data in BANKS:
            existing = session.query(Bank).filter_by(code=bank_data["code"]).first()
            if not existing:
                bank = Bank(**bank_data)
                session.add(bank)
                logger.info(f"Added bank: {bank_data['name']}")
            else:
                logger.info(f"Bank already exists: {bank_data['name']}")

        session.commit()

    logger.info("Seed completed")


if __name__ == "__main__":
    seed_banks()
