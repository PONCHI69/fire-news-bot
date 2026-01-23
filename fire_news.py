import requests
from bs4 import BeautifulSoup
import hashlib
import os
from datetime import datetime, timedelta

# =========================
# 基本設定
# =========================
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
SEEN_FILE = "seen_events.txt"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# =========================
# 關鍵字設定
# =========================
FIRE_KEYWORDS = [
    "fire", "blaze", "火災", "火警", "起火", "燒毀", "救災",
    "鋰電池", "太陽能", "儲能", "失火"
]

EXPLOSION_KEYWORDS = ["explosion", "爆炸", "氣爆", "洩漏"]

FACILITY_KEYWORDS = [
    "factory", "plant", "mill", "refinery", "warehouse",
    "工廠", "廠房", "倉儲", "工業", "化工", "石化", "煉油",
    "科技", "電子", "電廠", "園區", "中油", "台塑"
]

# ❗ 強制排除：演練 / 模擬（中英文）
EXCLUDE_KEYWORDS = [
    "模擬", "演練", "演習",
    "simulation", "drill", "exercise",
    "遊戲", "steam", "限免", "大亨",
    "缺工", "關稅", "股市", "講座", "論壇",
    "內閣", "選舉", "研討會", "營收", "房市"
]

# =========================
# 去重（事件層級）
# =========================
def event_key(title, link):
    return hashlib.sha256(f"{title}{link}".encode("utf-8")).hexdigest()

def is_duplicate(title, link):
    if not os.path.exists(SEEN_FILE):
        return False
    with open(SEEN_FILE, "r") as f:
        return event_key(title, link) in f.read().splitlines()

def save_event(title, link):
    with open(SEEN_FILE, "a") as f:
        f.write(event_key(title, link) + "\n")

# =========================
# 判斷邏輯
# =========================
def check_match(title):
    t = title.lower()
    if any(k in t for k in EXCLUDE_KEYWORDS):
        return False
    has_event = any(k in t for k in FIRE_KEYWORDS + EXPLOSION_KEYWORDS)
    has_place = any(k in t for k in FACILITY_KEYWORDS)
    return has_event and has_place

def get_severity(title):
    t = title.lower()
    if any(k in t for k in ["dead", "killed", "fatal", "死亡", "身亡"]):
        return "🚨 重大傷亡"
    if any(k in t for k in ["injured", "受傷"]):
        return "⚠️ 有人受傷"
    if any(k in t for k in EXPLOSION_KEYWORDS):
        return "💥 發生爆炸"
    return "🔥 火警通報"

# =========================
# 英文 → 中文翻譯（免 API Key）
# =========================
def translate_to_zh(text):
    try:
        res = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={
                "client": "gtx",
                "sl": "en",
                "tl": "zh-TW",
                "dt": "t",
                "q": text
            },
            timeout=10
        )
        return res.json()[0][0][0]
    except Exception:
        return "（翻譯失敗）"

# ======
