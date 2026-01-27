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
    "japan": "🇯🇵",
    "us": "🇺🇸",
    "america": "🇺🇸",
    "uk": "🇬🇧",
    "germany": "🇩🇪",
    "china": "🇨🇳",
    "taiwan": "🇹🇼",
}

# =========================
# 工具
# =========================
def sha(text):
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
    }[ch]

# =========================
# 核心事件去重
# =========================
def is_real_incident(title):
    t = title.lower()
    if any(k in t for k in EXCLUDE):
        return False
    return any(k in t for k in FIRE + EXPLOSION)

def extract_event_core(title):
    t = title.lower()
    event = "fire" if any(k in t for k in FIRE) else "explosion"
    location = next((k for k in COUNTRY_MAP if k in t), "unknown")
    return f"{location}-{event}"

def incident_fingerprint(title):
    return sha(extract_event_core(title))

# =========================
# 主流程
# =========================
def run():
    feeds = [
        "https://news.google.com/rss/search?q=(factory+OR+refinery)+(fire+OR+explosion)+when:12h",
        "https://news.google.com/rss/search?q=(工廠+OR+廠房)+(火災+OR+爆炸)+when:12h&hl=zh-TW"
    ]

    events = {}

    for url in feeds:
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.content, "xml")

        for item in soup.find_all("item"):
            title = item.title.text
            link = item.link.text
            pub = item.pubDate.text if item.pubDate else ""

            if not is_real_incident(title):
                continue

            fp = incident_fingerprint(title)
            events.setdefault(fp, {
                "title": title,
                "link": link,
                "pub": pub,
                "count": 0
            })
            events[fp]["count"] += 1

    for e in events.values():
        flag = detect_country(e["title"])
        channel = classify_channel(e["title"])
        webhook = webhook_by_channel(channel)

        msg = (
            f"{flag} **全球工業事故通報**\n"
            f"🔥 分類：`{channel}`\n"
            f"[{e['title']}](<{e['link']}>)\n"
            f"🧠 此事件已整合 `{e['count']}` 則新聞來源\n"
            f"🕒 時間：`{parse_time(e['pub'])}`"
        )

        requests.post(webhook, json={"content": msg}, timeout=10)

    if not events:
        requests.post(
            WEBHOOK_GENERAL,
            json={"content": "✅ 系統監測正常，12 小時內無新事故"},
            timeout=10
        )

if __name__ == "__main__":
    run()
