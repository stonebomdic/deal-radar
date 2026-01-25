import random
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup
from loguru import logger
from playwright.sync_api import sync_playwright

from src.config import get_settings

settings = get_settings()

USER_AGENTS = [
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    ),
]


def get_random_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    }


def random_delay():
    delay = random.uniform(settings.crawler_delay_min, settings.crawler_delay_max)
    time.sleep(delay)


def fetch_page(url: str, retries: Optional[int] = None) -> Optional[BeautifulSoup]:
    if retries is None:
        retries = settings.crawler_max_retries

    for attempt in range(retries):
        try:
            random_delay()
            response = requests.get(url, headers=get_random_headers(), timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.text, "lxml")
        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt + 1}/{retries} failed for {url}: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)

    logger.error(f"Failed to fetch {url} after {retries} attempts")
    return None


def fetch_page_with_browser(
    url: str, wait_selector: Optional[str] = None, timeout: int = 30000
) -> Optional[BeautifulSoup]:
    """使用 Playwright 瀏覽器獲取頁面內容，可處理 JavaScript 渲染的頁面"""
    try:
        random_delay()
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080},
                locale="zh-TW",
            )
            page = context.new_page()

            # 設定額外的 headers
            page.set_extra_http_headers({
                "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            })

            page.goto(url, wait_until="networkidle", timeout=timeout)

            # 等待特定元素出現
            if wait_selector:
                page.wait_for_selector(wait_selector, timeout=timeout)
            else:
                # 等待頁面完全載入
                page.wait_for_load_state("networkidle")
                time.sleep(2)  # 額外等待確保動態內容載入

            html = page.content()
            browser.close()

            return BeautifulSoup(html, "lxml")
    except Exception as e:
        logger.error(f"Failed to fetch {url} with browser: {e}")
        return None
