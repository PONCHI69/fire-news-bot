import requests
from bs4 import BeautifulSoup
import hashlib
import os
import re
from datetime import datetime, timedelta

# =========================
# Discord Webhooks
# =========================
WEBHOOK_GENERAL = os.getenv("DISCORD_WEBHOOK_GENERAL")
WEBHOOK_CHEMICAL = os.getenv("DISCORD_WEBHOOK_CHEMICAL")
WEBHOOK_ENERGY = os.getenv("DISCORD_WEBHOOK_ENERGY")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# =========================
# 關鍵字設定
# =========================
FIRE = ["fire", "blaze", "火災", "火警", "起火", "失火"]
EXPLOSION = ["explosion", "爆炸", "氣爆"]

CHEMICAL = ["chemical", "petrochemical", "refinery", "石化", "化工", "煉油", "油庫"]
ENERGY = ["power", "plant", "電廠", "變電所", "儲能", "太陽能", "鋰電池"]
TECH = ["semiconductor", "electronics", "wafer", "半導體", "電子", "面板"]
BUILDING = ["building", "apartment", "skyscraper", "大樓", "住宅", "公寓"]

EXCLUDE = [
    "演練", "模擬", "演習", "訓練", "simulation", "drill",
    "股市", "論壇", "政策", "財報", "營收", "調查", "委員會",
    "原因仍未確定", "起火成因", "防火", "預防", "宣導"
]

COUNTRY_MAP = {
    "greece": "🇬🇷",
    "japan": "🇯🇵",
    "us": "🇺🇸",
    "u.s.": "🇺🇸",
    "america": "🇺🇸",
    "uk": "🇬🇧",
    "germany": "🇩🇪",
    "china": "🇨🇳",
    "taiwan": "🇹🇼",
}

# =========================
# 工具
# =========================
def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def parse_time(pub):
    try:
        gmt = datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %Z")
        return (gmt + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")
    except:
        return "未知"

def detect_country(text):
    t = text.lower()
    for k, flag in COUNTRY_MAP.items():
        if k in t:
            return flag
    return "🌍"

def classify_channel(title):
    t = title.lower()
    if any(k in t for k in CHEMICAL):
        return "CHEMICAL"
    if any(k in t for k in ENERGY):
        return "ENERGY"
    if any(k in t for k in TECH):
        return "TECH"
    if any(k in t for k in BUILDING):
        return "BUILDING"
    return "GENERAL"

def webhook_by_channel(ch):
    return {
        "CHEMICAL": WEBHOOK_CHEMICAL,
        "ENERGY": WEBHOOK_ENERGY,
        "TECH": WEBHOOK_GENERAL,
        "BUILDING": WEBHOOK_GENERAL,
        "GENERAL": WEBHOOK_GENERAL,
    }.get(ch, WEBHOOK_GENERAL)

# =========================
# 翻譯（只翻非中文）
# =========================
def contains_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))

def translate_to_zh(text: str) -> str:
    try:
        r = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={
                "client": "gtx",
                "sl": "auto",
                "tl": "zh-TW",
                "dt": "t",
                "q": text,
            },
            timeout=10,
        )
        return r.json()[0][0][0]
    except:
        return text

# =========================
# 事件層級去重（核心）
# =========================
def is_real_incident(title):
    t = title.lower()
    if any(k in t for k in EXCLUDE):
        return False
    return any(k in t for k in FIRE + EXPLOSION)

def extract_event_core(title):
    """
    事件唯一鍵 = 國家 + 設施 + 災害類型
    """
    t = title.lower()

    event_type = "fire" if any(k in t for k in FIRE) else "explosion"

    facility_keywords = [
        "factory", "plant", "refinery", "semiconductor",
        "工廠", "廠房", "食品廠", "餅乾", "煉油廠"
    ]
    facility = next((k for k in facility_keywords if k in t), "site")

    location = next((k for k in COUNTRY_MAP.keys() if k in t), "unknown")

    return f"{location}-{facility}-{event_type}"

def incident_fingerprint(title):
    return sha(extract_event_core(title))

# =========================
# 即時監測（單 run 完整去重）
# =========================
def run_realtime():
    feeds = [
        "https://news.google.com/rss/search?q=(factory+OR+industrial+OR+refinery+OR+semiconductor)+(fire+OR+explosion)+when:12h&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=(工廠+OR+廠房+OR+食品廠+OR+大樓)+(火災+OR+爆炸)+when:12h&hl=zh-TW&gl=TW&ceid=TW:zh-tw",
    ]

    # 單次執行事件池（不吃檔案）
    event_pool = {}

    for url in feeds:
        try:
            res = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.content, "xml")

            for item in soup.find_all("item")[:40]:
                title = item.title.text
                link = item.link.text
                pub = item.pubDate.text if item.pubDate else ""

                if not is_real_incident(title):
                    continue

                fp = incident_fingerprint(title)

                if fp not in event_pool:
                    event_pool[fp] = {
                        "titles": [title],
                        "links": [link],
                        "pub": pub,
                    }
                else:
                    event_pool[fp]["titles"].append(title)
                    event_pool[fp]["links"].append(link)

        except Exception as e:
            print(f"RSS 讀取錯誤: {e}")

    # 發送整合後事件
    for fp, data in event_pool.items():
        main_title = data["titles"][0]
        link = data["links"][0]
        source_count = len(data["titles"])

        flag = detect_country(main_title)
        channel = classify_channel(main_title)
        webhook = webhook_by_channel(channel)

        # 翻譯判斷
        if contains_chinese(main_title):
            display_title = main_title
        else:
            zh_title = translate_to_zh(main_title)
            display_title = f"{main_title}\n（{zh_title}）"

        msg = (
            f"{flag} **全球工業事故通報**\n"
            f"🔥 分類：`{channel}`\n"
            f"[{display_title}](<{link}>)\n"
            f"🧠 此事件已整合 `{source_count}` 則新聞來源\n"
            f"🕒 時間：`{parse_time(data['pub'])}`"
        )

        requests.post(webhook, json={"content": msg}, timeout=10)

    if not event_pool:
        requests.post(
            WEBHOOK_GENERAL,
            json={"content": "✅ **系統監測正常**\n過去 12 小時內無新增工業事故新聞。"},
            timeout=10,
        )

# =========================
# 入口
# =========================
if __name__ == "__main__":
    run_realtime()
