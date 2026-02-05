import argparse

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.config import get_settings
from src.crawlers.banks import (
    CathayCrawler,
    CtbcCrawler,
    EsunCrawler,
    FirstbankCrawler,
    FubonCrawler,
    HncbCrawler,
    MegabankCrawler,
    SinopacCrawler,
    TaishinCrawler,
    UbotCrawler,
)
from src.db.database import Base

settings = get_settings()
sync_database_url = settings.database_url.replace("+aiosqlite", "")


def init_database():
    """初始化資料庫"""
    engine = create_engine(sync_database_url)
    Base.metadata.create_all(engine)
    logger.info("Database initialized")


def run_crawler(bank: str = None):
    """執行爬蟲"""
    engine = create_engine(sync_database_url)

    crawlers = {
        "cathay": CathayCrawler,
        "ctbc": CtbcCrawler,
        "esun": EsunCrawler,
        "firstbank": FirstbankCrawler,
        "fubon": FubonCrawler,
        "hncb": HncbCrawler,
        "megabank": MegabankCrawler,
        "sinopac": SinopacCrawler,
        "taishin": TaishinCrawler,
        "ubot": UbotCrawler,
    }

    with Session(engine) as session:
        if bank:
            if bank not in crawlers:
                logger.error(f"Unknown bank: {bank}. Available: {list(crawlers.keys())}")
                return
            crawler = crawlers[bank](session)
            result = crawler.run()
            logger.info(f"Result: {result}")
        else:
            for name, crawler_cls in crawlers.items():
                logger.info(f"Running crawler for {name}")
                crawler = crawler_cls(session)
                result = crawler.run()
                logger.info(f"Result: {result}")


def main():
    parser = argparse.ArgumentParser(description="Credit Card Crawler CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # init command
    subparsers.add_parser("init", help="Initialize database")

    # crawl command
    crawl_parser = subparsers.add_parser("crawl", help="Run crawler")
    crawl_parser.add_argument("--bank", "-b", help="Bank code (e.g., ctbc)")

    # serve command
    subparsers.add_parser("serve", help="Start API server")

    # seed command
    subparsers.add_parser("seed", help="Seed initial bank data")

    args = parser.parse_args()

    if args.command == "init":
        init_database()
    elif args.command == "crawl":
        run_crawler(args.bank)
    elif args.command == "serve":
        import uvicorn

        uvicorn.run(
            "src.main:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=settings.debug,
        )
    elif args.command == "seed":
        from src.db.seed import seed_banks

        seed_banks()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
