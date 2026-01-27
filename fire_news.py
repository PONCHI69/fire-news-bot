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

# 災害關鍵字
FIRE = ["fire", "blaze", "火災", "火警", "起火", "失火"]
EXPLOSION = ["explosion", "爆炸", "氣爆"]

# 分流關鍵字
CHEMICAL = ["chemical", "petrochemical", "refinery", "石化", "化工", "煉油"]
ENERGY = ["power", "plant", "電廠", "變電所", "儲能", "太陽能", "鋰電池"]
TECH = ["semiconductor", "electronics", "wafer", "半導體", "電子"]
BUILDING = ["building", "apartment", "skyscraper", "大樓", "住宅"]

# 排除雜訊關鍵字 (已加入培訓、房屋等非事故詞彙)
EXCLUDE = [
    "演練", "模擬", "演習", "訓練", "simulation", "drill", "exercise", "training",
    "股市", "政策", "調查", "委員會", "報告", "原因仍未確定", "起火成因", "日前",
    "housing", "房屋", "宣導", "平安符", "點燃市場", "壞兔子", "點燃蘋果"
]

COUNTRY_MAP = {
    "greece": "🇬🇷", "japan": "🇯🇵", "us": "🇺🇸", "u.s.": "🇺🇸", "america": "🇺🇸",
    "uk": "🇬🇧", "germany": "🇩🇪", "china": "🇨🇳", "taiwan": "🇹🇼"
}

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
    """提取事故核心特徵以產生唯一指紋"""
    t = title.lower()
    # 偵測災害與設施 (加入同義詞轉換)
    event_type = "fire" if any(k in t for k in FIRE) else "explosion"
    t = t.replace("cookie", "biscuit")
    facility_keywords = ["refinery", "biscuit", "factory", "plant", "semiconductor", "warehouse", "工廠", "廠房", "餅乾", "煉油廠"]
    facility = next((k for k in facility_keywords if k in t), "industrial_site")
    location = next((k for k in COUNTRY_MAP.keys() if k in t), "global")
    # 移除數字(死傷)與雜訊字元
    t_clean = re.sub(r"\d+", "", t)
    t_clean = re.sub(r"[^a-z\u4e00-\u9fff]", "", t_clean)
    return hashlib.sha256(f"{location}-{facility}-{event_type}".encode()).hexdigest()

def detect_country(text):
    t = text.lower()
    for k, flag in COUNTRY_MAP.items():
        if k in t: return flag
    return "🌍"

def classify_channel(title):
    t = title.lower()
    if any(k in t for k in CHEMICAL): return "CHEMICAL"
    if any(k in t for k in ENERGY): return "ENERGY"
    if any(k in t for k in TECH): return "TECH"
    if any(k in t for k in BUILDING): return "BUILDING"
    return "GENERAL"

def webhook_by_channel(ch):
    mapping = {"CHEMICAL": WEBHOOK_CHEMICAL, "ENERGY": WEBHOOK_ENERGY, "TECH": WEBHOOK_GENERAL, "BUILDING": WEBHOOK_GENERAL}
    return mapping.get(ch, WEBHOOK_GENERAL)

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
                # 跨次執行去重：如果檔案裡已經看過這個事件指紋，直接跳過
                if fp in seen_events: continue

                if fp not in event_pool:
                    event_pool[fp] = {"titles": [title], "link": item.link.text, "pub": item.pubDate.text}
                else:
                    if title not in event_pool[fp]["titles"]:
                        event_pool[fp]["titles"].append(title)
        except Exception as e: print(f"RSS 錯誤: {e}")

    sent_count = 0
    for fp, data in event_pool.items():
        main_title = sorted(data["titles"], key=len)[len(data["titles"])//2]
        flag = detect_country(main_title)
        channel = classify_channel(main_title)
        webhook = webhook_by_channel(channel)
        
        # 標題翻譯 (非台非中才翻)
        is_chinese = bool(re.search(r"[\u4e00-\u9fff]", main_title))
        display_title = f"{main_title}\n（{translate_to_zh(main_title)}）" if not is_chinese else main_title
        
        msg = (
            f"{flag} **全球工業事故通報**\n"
            f"🔥 分類：`{channel}`\n"
            f"[{display_title}](<{data['link']}>)\n"
            f"🧠 此事件已整合 `{len(data['titles'])}` 則新聞來源\n"
            f"🕒 時間：`{data['pub']}`"
        )
        
        requests.post(webhook, json={"content": msg}, timeout=10)
        seen_events[fp] = now.isoformat()
        sent_count += 1

    # 心跳機制
    if sent_count == 0:
        requests.post(WEBHOOK_GENERAL, json={"content": "✅ **系統監測正常**\n系統設定的前 12 個小時內，無新增工業事故新聞。"})

    save_seen(seen_events)

if __name__ == "__main__":
    run_realtime()
