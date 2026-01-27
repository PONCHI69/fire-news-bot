import requests
from bs4 import BeautifulSoup
import hashlib
import os
import re
import json
from datetime import datetime, timedelta

# =========================
# 配置
# =========================
WEBHOOK_GENERAL = os.getenv("DISCORD_WEBHOOK_GENERAL")
WEBHOOK_CHEMICAL = os.getenv("DISCORD_WEBHOOK_CHEMICAL")
WEBHOOK_ENERGY = os.getenv("DISCORD_WEBHOOK_ENERGY")

SEEN_FILE = "seen_events.json"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# 關鍵字設定
FIRE = ["fire", "blaze", "火災", "火警", "起火", "失火"]
EXPLOSION = ["explosion", "爆炸", "氣爆"]
CHEMICAL = ["chemical", "petrochemical", "refinery", "石化", "化工", "煉油"]
ENERGY = ["power", "plant", "電廠", "變電所", "儲能", "太陽能", "鋰電池"]
TECH = ["semiconductor", "electronics", "wafer", "半導體", "電子"]
BUILDING = ["building", "apartment", "skyscraper", "大樓", "住宅"]

EXCLUDE = ["演練", "模擬", "演習", "訓練", "simulation", "drill", "股市", "政策", "調查", "原因仍未確定"]

COUNTRY_MAP = {"greece": "🇬🇷", "japan": "🇯🇵", "us": "🇺🇸", "u.s.": "🇺🇸", "uk": "🇬🇧", "china": "🇨🇳", "taiwan": "🇹🇼"}

# =========================
# 工具函式
# =========================
def load_seen():
    if not os.path.exists(SEEN_FILE): return {}
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_seen(data):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def translate_to_zh(text):
    try:
        res = requests.get("https://translate.googleapis.com/translate_a/single",
                           params={"client": "gtx", "sl": "auto", "tl": "zh-TW", "dt": "t", "q": text}, timeout=10)
        return res.json()[0][0][0]
    except: return text

def extract_event_core(title):
    t = title.lower()
    event_type = "fire" if any(k in t for k in FIRE) else "explosion"
    # 增加更多設施關鍵字以利去重
    facility_keywords = ["factory", "plant", "refinery", "cookie", "biscuit", "工廠", "廠房", "餅乾"]
    facility = next((k for k in facility_keywords if k in t), "site")
    location = next((k for k in COUNTRY_MAP.keys() if k in t), "unknown")
    return hashlib.sha256(f"{location}-{facility}-{event_type}".encode()).hexdigest()

def detect_country(text):
    t = text.lower()
    for k, flag in COUNTRY_MAP.items():
        if k in t: return flag
    return "🌍"

# =========================
# 核心執行
# =========================
def run_realtime():
    seen_events = load_seen()
    feeds = [
        "https://news.google.com/rss/search?q=(factory+OR+industrial+OR+refinery)+(fire+OR+explosion)+when:12h&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=(工廠+OR+廠房+OR+食品廠)+(火災+OR+爆炸)+when:12h&hl=zh-TW&gl=TW&ceid=TW:zh-tw",
    ]

    event_pool = {}
    now = datetime.now()

    for url in feeds:
        try:
            res = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.content, "xml")
            for item in soup.find_all("item")[:40]:
                title = item.title.text
                if any(k in title.lower() for k in EXCLUDE): continue
                if not any(k in title.lower() for k in FIRE + EXPLOSION): continue

                fp = extract_event_core(title)
                # 跨次去重：如果檔案裡已經看過這個指紋，直接跳過整組合併
                if fp in seen_events: continue

                if fp not in event_pool:
                    event_pool[fp] = {"titles": [title], "link": item.link.text, "pub": item.pubDate.text}
                else:
                    event_pool[fp]["titles"].append(title)
        except Exception as e: print(f"RSS 錯誤: {e}")

    # 發送新事件
    sent_count = 0
    for fp, data in event_pool.items():
        main_title = data["titles"][0]
        flag = detect_country(main_title)
        display_title = f"{main_title}\n（{translate_to_zh(main_title)}）" if flag != "🇹🇼" else main_title
        
        msg = (
            f"{flag} **全球工業事故通報**\n"
            f"[{display_title}](<{data['link']}>)\n"
            f"🧠 此事件已整合 `{len(data['titles'])}` 則新聞來源\n"
            f"🕒 時間：`{data['pub']}`"
        )
        
        requests.post(WEBHOOK_GENERAL, json={"content": msg}, timeout=10)
        seen_events[fp] = now.isoformat()
        sent_count += 1

    if sent_count == 0:
        requests.post(WEBHOOK_GENERAL, json={"content": "✅ **系統監測正常**\n過去 12 小時內無新增工業事故新聞。"})

    save_seen(seen_events)

if __name__ == "__main__":
    run_realtime()
