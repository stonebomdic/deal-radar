import random
import re
import time
from typing import List, Optional

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


# ============================================================================
# 文字清理工具（用於優惠活動擷取）
# ============================================================================

# 網頁導航、UI 元素等雜訊關鍵字
NOISE_KEYWORDS = [
    # 導航元素
    "首頁", "返回", "上一頁", "下一頁", "更多", "瞭解更多", "了解更多",
    "立即申辦", "立即辦卡", "立即申請", "馬上申請", "線上申辦",
    "Prev", "Next", "Previous", "Skip", "Menu",
    # UI 元素
    "點擊", "按此", "請點選", "展開", "收合", "關閉", "開啟",
    # 頁面區塊
    "專屬禮遇", "附加權益", "回饋計劃", "申辦說明", "注意事項",
    "謹慎理財", "信用至上", "循環年利率",
    # 網站結構
    "脆饗食", "脆萌寵", "脆好購", "脆慢活", "點數生活圈",
    # 頁尾
    "隱私權", "服務條款", "聯絡我們", "客服專線", "Copyright",
]

# 需要移除的 pattern
NOISE_PATTERNS = [
    r"Previous\s*Next",
    r"\d{6,}",  # 長數字序列（如電話號碼）
    r"[\u2460-\u2473]",  # 圓圈數字 ①②③
    r"[►▶◀◄→←↑↓]",  # 箭頭符號
    r"\s{3,}",  # 連續空白
]


def clean_text(text: str) -> str:
    """清理文字，移除多餘空白和雜訊字元"""
    if not text:
        return ""

    # 移除多餘換行和空白
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s+", " ", text)

    # 移除雜訊 pattern
    for pattern in NOISE_PATTERNS:
        text = re.sub(pattern, " ", text)

    return text.strip()


def clean_promotion_title(title: str, max_length: int = 60) -> str:
    """清理優惠活動標題

    Args:
        title: 原始標題文字
        max_length: 最大長度

    Returns:
        清理後的標題
    """
    if not title:
        return ""

    # 基本清理
    title = clean_text(title)

    # 移除導航雜訊
    for noise in NOISE_KEYWORDS:
        title = title.replace(noise, " ")

    # 移除連續空白
    title = re.sub(r"\s+", " ", title).strip()

    # 移除開頭的標點符號
    title = re.sub(r"^[，。、；：\s]+", "", title)

    # 移除結尾的不完整文字（以常見連接詞結尾）
    title = re.sub(r"[，。、；：及和與或]\s*$", "", title)

    # 截斷過長的標題
    if len(title) > max_length:
        # 嘗試在標點處截斷
        for punct in ["，", "。", "、", " "]:
            idx = title.rfind(punct, 0, max_length)
            if idx > max_length // 2:
                title = title[:idx]
                break
        else:
            title = title[:max_length]

    return title.strip()


def is_valid_promotion(title: str, min_length: int = 5) -> bool:
    """驗證優惠活動是否有效

    Args:
        title: 優惠標題
        min_length: 最小長度

    Returns:
        是否為有效優惠
    """
    if not title or len(title) < min_length:
        return False

    # 檢查是否主要由雜訊組成
    noise_count = sum(1 for noise in NOISE_KEYWORDS if noise in title)
    if noise_count >= 3:
        return False

    # 排除免責聲明、注意事項（但保留包含「%」的回饋描述）
    disclaimer_keywords = [
        "無法回饋", "不適用", "不包含", "恕不", "將可能",
        "請詳見", "請參閱", "依各", "依本行", "為準", "不具",
        "追回", "保留", "權利", "取消資格",
    ]
    # 如果有「%」和「回饋」，可能是有效優惠，不要過濾
    has_reward = "%" in title and "回饋" in title
    if not has_reward and any(kw in title for kw in disclaimer_keywords):
        return False

    # 必須包含有意義的內容（回饋、優惠相關關鍵字）
    meaningful_keywords = [
        "%", "回饋", "優惠", "折扣", "減免", "贈", "禮", "免費",
        "加碼", "首刷", "新戶", "滿額", "分期", "紅利",
    ]
    if not any(kw in title for kw in meaningful_keywords):
        return False

    return True


def extract_reward_rate(text: str) -> Optional[float]:
    """從文字中擷取回饋率

    Args:
        text: 包含回饋率的文字

    Returns:
        回饋率（百分比），若無則返回 None
    """
    if not text:
        return None

    # 尋找百分比數字
    patterns = [
        r"(\d+(?:\.\d+)?)\s*%\s*(?:回饋|現金回饋)",
        r"最高\s*(\d+(?:\.\d+)?)\s*%",
        r"(\d+(?:\.\d+)?)\s*%",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                rate = float(match.group(1))
                # 合理範圍檢查
                if 0 < rate <= 30:
                    return rate
            except ValueError:
                pass

    return None


def extract_promotions_from_text(
    text: str,
    max_count: int = 3,
) -> List[dict]:
    """從頁面文字中擷取優惠活動

    Args:
        text: 頁面文字內容
        max_count: 最大優惠數量

    Returns:
        優惠活動列表，每個包含 title, description, reward_rate
    """
    if not text:
        return []

    # 清理文字
    text = clean_text(text)

    promotions = []
    seen_rates = set()  # 用來避免重複的回饋率

    # 優惠擷取 pattern（優先順序）
    # 使用更精確的終止條件：遇到下一個優惠開頭或特定邊界詞就停止
    boundary = r"(?=\s*(?:＊|注意|活動期間|詳見|使用|持卡|消費明細|$))"

    patterns = [
        # 最高 X% 回饋（最常見格式）
        rf"(最高\s*(?:享\s*)?\d+(?:\.\d+)?\s*%\s*(?:回饋|現金回饋|點數回饋)?){boundary}",
        # 國內/國外消費回饋
        rf"((?:國內|國外|海外)(?:實體)?(?:商店)?消費[^＊]*?\d+(?:\.\d+)?\s*%(?:\s*回饋)?){boundary}",
        # 特定類別回饋
        rf"((?:餐飲|網購|超商|交通|百貨|旅遊|行動支付|加油)[^＊]*?\d+(?:\.\d+)?\s*%(?:\s*回饋)?){boundary}",
        # 新戶/首刷優惠
        r"((?:新戶|首刷|新卡)(?:享|禮|贈|回饋)[^。，＊]{5,30})",
        # 分期優惠
        r"(\d+期\s*(?:0利率|零利率)(?:優惠)?)",
        # 滿額優惠
        r"(滿(?:額)?[^。，＊]*?(?:贈|送|享|回饋)[^。，＊]{5,25})",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            title = clean_promotion_title(match)

            if not title:
                continue

            if not is_valid_promotion(title):
                continue

            # 提取回饋率用於去重
            reward_rate = extract_reward_rate(title)

            # 避免重複：相同回饋率且標題相似
            rate_key = f"{reward_rate or 0:.1f}"
            if rate_key in seen_rates:
                # 如果已經有這個回饋率，跳過相似的標題
                is_duplicate = any(
                    (title[:15] in existing["title"] or existing["title"][:15] in title)
                    for existing in promotions
                )
                if is_duplicate:
                    continue

            seen_rates.add(rate_key)

            promotions.append({
                "title": title,
                "description": title,
                "reward_rate": reward_rate,
            })

            if len(promotions) >= max_count:
                return promotions

    return promotions


def detect_promotion_category(text: str) -> str:
    """根據文字判斷優惠類別

    Args:
        text: 優惠文字

    Returns:
        類別代碼
    """
    category_keywords = {
        "dining": ["餐飲", "美食", "餐廳", "吃", "用餐"],
        "online_shopping": ["網購", "線上", "電商", "蝦皮", "momo", "Yahoo", "PChome"],
        "transport": ["交通", "加油", "高鐵", "台鐵", "捷運", "停車"],
        "overseas": ["海外", "國外", "出國", "日本", "韓國", "國際"],
        "convenience_store": ["超商", "7-11", "全家", "萊爾富", "OK"],
        "department_store": ["百貨", "週年慶", "SOGO", "新光", "遠東", "微風"],
        "travel": ["旅遊", "哩程", "里程", "飛行", "航空", "機場", "訂房", "飯店"],
        "mobile_pay": ["行動支付", "Apple Pay", "Google Pay", "Samsung Pay", "LINE Pay"],
        "supermarket": ["超市", "全聯", "家樂福", "大潤發", "costco"],
    }

    for category, keywords in category_keywords.items():
        if any(kw in text for kw in keywords):
            return category

    return "others"
