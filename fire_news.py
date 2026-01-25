import requests
from bs4 import BeautifulSoup
import hashlib
import os
from datetime import datetime, timedelta
import re

# =========================
# Discord Webhooks
# =========================
WEBHOOK_GENERAL = os.getenv("DISCORD_WEBHOOK_GENERAL")
WEBHOOK_CHEMICAL = os.getenv("DISCORD_WEBHOOK_CHEMICAL")
WEBHOOK_ENERGY = os.getenv("DISCORD_WEBHOOK_ENERGY")

SEEN_FILE = "seen_events.txt"
SUMMARY_FILE = "daily_summary.txt"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# =========================
# 關鍵字設定
# =========================
FIRE = ["fire", "blaze", "火災", "火警", "起火", "失火"]
EXPLOSION = ["explosion", "爆炸", "氣爆"]

CHEMICAL = ["chemical", "petrochemical", "refinery", "石化", "化工", "煉油", "油庫"]
ENERGY = ["power", "plant", "電廠", "變電所", "儲能", "太陽能", "鋰電池"]

EXCLUDE = [
    "演練", "模擬", "演習", "訓練", "simulation", "drill", "exercise",
    "遊戲", "steam", "股市", "論壇", "活動"
]

COUNTRY_MAP = {
    "japan": "🇯🇵", "tokyo": "🇯🇵",
    "us": "🇺🇸", "u.s.": "🇺🇸", "america": "🇺🇸",
    "germany": "🇩🇪", "berlin": "🇩🇪",
    "uk": "🇬🇧", "london": "🇬🇧",
    "canada": "🇨🇦",
    "india": "🇮🇳",
    "china": "🇨🇳",
    "taiwan": "🇹🇼"
}

# =========================
# 基礎工具
# =========================
def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()

def load_set(path):
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        return set(f.read().splitlines())

def save_set(path, s):
    with open(path, "w") as f:
        f.write("\n".join(s))

def translate_to_zh(text):
    """將標題翻譯為中文"""
    try:
        res = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "auto", "tl": "zh-TW", "dt": "t", "q": text}, 
            timeout=10
        )
        return res.json()[0][0][0]
    except:
        return text # 翻譯失敗則回傳原標題

SEEN = load_set(SEEN_FILE)
SUMMARY = load_set(SUMMARY_FILE)

# =========================
# 核心邏輯
# =========================
def is_real_incident(title):
    t = title.lower()
    if any(k in t for k in EXCLUDE):
        return False
    return any(k in t for k in FIRE + EXPLOSION)

def incident_fingerprint(title):
    key = re.sub(r"[^a-zA-Z\u4e00-\u9fff]", "", title.lower())
    return sha(key[:40])

def detect_country(title, link):
    text = (title + " " + link).lower()
    for k, flag in COUNTRY_MAP.items():
        if k in text:
            return flag
    return "🌍"

def classify_channel(title):
    t = title.lower()
    if any(k in t for k in CHEMICAL):
        return "CHEMICAL"
    if any(k in t for k in ENERGY):
        return "ENERGY"
    return "GENERAL"

def webhook_by_channel(ch):
    return {
        "CHEMICAL": WEBHOOK_CHEMICAL,
        "ENERGY": WEBHOOK_ENERGY,
        "GENERAL": WEBHOOK_GENERAL
    }.get(ch)

def parse_time(pub):
    try:
        gmt = datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %Z")
        return (gmt + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")
    except:
        return "未知"

def send(webhook, msg):
    if webhook:
        requests.post(webhook, json={"content": msg}, timeout=10)

# =========================
# 即時監測
# =========================
def run_realtime():
    feeds = [
        "https://news.google.com/rss/search?q=(factory+OR+industrial+OR+refinery)+(fire+OR+explosion)+when:12h&hl=en&gl=US&ceid=US:en"
    ]

    for url in feeds:
        try:
            soup = BeautifulSoup(requests.get(url, headers=HEADERS, timeout=15).content, "xml")
            for item in soup.find_all("item")[:30]:
                title = item.title.text
                link = item.link.text
                pub = item.pubDate.text if item.pubDate else ""

                if not is_real_incident(title):
                    continue

                fp = incident_fingerprint(title)
                if fp in SEEN:
                    SUMMARY.add(fp)
                    continue

                flag = detect_country(title, link)
                channel = classify_channel(title)
                webhook = webhook_by_channel(channel)

                # 國際新聞執行翻譯，台灣新聞維持原標題
                display_title = translate_to_zh(title) if flag != "🇹🇼" else title

                msg = (
                    f"{flag} **全球工業事故**\n"
                    f"🔥 `{channel}`\n"
                    f"[{display_title}](<{link}>)\n"
                    f"🕒 `{parse_time(pub)}`"
                )

                send(webhook, msg)
                SEEN.add(fp)
                SUMMARY.add(fp)
        except Exception as e:
            print(f"錯誤: {e}")

    save_set(SEEN_FILE, SEEN)
    save_set(SUMMARY_FILE, SUMMARY)

# =========================
# 每日摘要
# =========================
def run_daily_summary():
    if not SUMMARY:
        return

    msg = "🗞 **24h 工業事故摘要**\n"
    msg += f"共 {len(SUMMARY)} 起已合併事故"

    send(WEBHOOK_GENERAL, msg)
    SUMMARY.clear()
    save_set(SUMMARY_FILE, SUMMARY)

# =========================
# 入口
# =========================
if __name__ == "__main__":
    mode = os.getenv("MODE", "realtime")
    if mode == "summary":
        run_daily_summary()
    else:
        run_realtime()
