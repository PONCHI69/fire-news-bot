import requests
from bs4 import BeautifulSoup
import hashlib
import os
from datetime import datetime, timedelta
import re
import json

# =========================
# Discord Webhooks
# =========================
WEBHOOK_GENERAL = os.getenv("DISCORD_WEBHOOK_GENERAL")
WEBHOOK_CHEMICAL = os.getenv("DISCORD_WEBHOOK_CHEMICAL")
WEBHOOK_ENERGY = os.getenv("DISCORD_WEBHOOK_ENERGY")

SEEN_FILE = "seen_events.json" # 改用 JSON 存儲帶時間戳的紀錄
SUMMARY_FILE = "daily_summary.txt"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# =========================
# 關鍵字設定
# =========================
FIRE = ["fire", "blaze", "火災", "火警", "起火", "失火"]
EXPLOSION = ["explosion", "爆炸", "氣爆"]

CHEMICAL = ["chemical", "petrochemical", "refinery", "石化", "化工", "煉油", "油庫"]
ENERGY = ["power", "plant", "電廠", "變電所", "儲能", "太陽能", "鋰電池"]
TECH = ["semiconductor", "electronics", "wafer", "半導體", "科技", "電子", "面板", "光電", "積體電路"]
BUILDING = ["building", "apartment", "skyscraper", "大樓", "商辦", "住宅", "公寓", "建築"]

EXCLUDE = ["演練", "模擬", "演習", "訓練", "simulation", "drill", "exercise", "遊戲", "steam", "股市", "論壇", "活動"]
EXCLUDE += ["稅收", "股價", "財報", "營收", "總統", "選戰", "政策", "趨勢", "熱情", "點燃蘋果", "稅收政策"]

COUNTRY_MAP = {
    "japan": "🇯🇵", "tokyo": "🇯🇵", "us": "🇺🇸", "u.s.": "🇺🇸", "america": "🇺🇸",
    "germany": "🇩🇪", "berlin": "🇩🇪", "uk": "🇬🇧", "london": "🇬🇧",
    "canada": "🇨🇦", "india": "🇮🇳", "china": "🇨🇳", "taiwan": "🇹🇼"
}

# =========================
# 基礎工具與持久化
# =========================
def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()

def load_seen():
    if not os.path.exists(SEEN_FILE):
        return {}
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_seen(data):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

def load_set(path):
    if not os.path.exists(path): return set()
    with open(path, "r", encoding="utf-8") as f:
        return set(f.read().splitlines())

def save_set(path, s):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(s))

# =========================
# 核心邏輯 (事件指紋強化)
# =========================
def normalize_event_text(title):
    t = title.lower()
    t = re.sub(r"\d+", "", t) # 1. 移除數字
    noise_words = ["至少", "最新", "消息", "快訊", "更新", "造成", "導致", "死亡", "失蹤", "受傷", "報導", "指出", "表示"]
    for w in noise_words: # 2. 移除雜訊詞
        t = t.replace(w, "")
    t = re.sub(r"[^a-z\u4e00-\u9fff]", "", t) # 3. 只保留中英文
    return t[:30] # 4. 截短

def incident_fingerprint(title):
    normalized = normalize_event_text(title)
    return sha(normalized)

def detect_country(title, link):
    """根據標題或連結偵測國家，並回傳國旗圖示"""
    text = (title + " " + link).lower()
    for k, flag in COUNTRY_MAP.items():
        if k in text:
            return flag
    return "🌍"

def is_real_incident(title):
    t = title.lower()
    if any(k in t for k in EXCLUDE): return False
    has_event = any(k in t for k in FIRE + EXPLOSION)
    is_metaphor = any(k in t for k in ["點燃蘋果", "點燃市場", "點燃趨勢"])
    is_prevention = any(k in t for k in ["防火", "預防", "宣導", "平安符"])
    return has_event and not is_metaphor and not is_prevention

def translate_to_zh(text):
    try:
        res = requests.get("https://translate.googleapis.com/translate_a/single",
                           params={"client": "gtx", "sl": "auto", "tl": "zh-TW", "dt": "t", "q": text}, timeout=10)
        return res.json()[0][0][0]
    except:
        return text

def classify_channel(title):
    t = title.lower()
    if any(k in t for k in CHEMICAL): return "CHEMICAL"
    if any(k in t for k in ENERGY): return "ENERGY"
    if any(k in t for k in TECH): return "TECH"
    if any(k in t for k in BUILDING): return "BUILDING"
    return "GENERAL"

def webhook_by_channel(ch):
    return {"CHEMICAL": WEBHOOK_CHEMICAL, "ENERGY": WEBHOOK_ENERGY, "TECH": WEBHOOK_GENERAL, "BUILDING": WEBHOOK_GENERAL, "GENERAL": WEBHOOK_GENERAL}.get(ch)

def parse_time(pub):
    try:
        gmt = datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %Z")
        return (gmt + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")
    except:
        return "未知"

# =========================
# 即時監測
# =========================
SEEN_EVENTS = load_seen()
SUMMARY = load_set(SUMMARY_FILE)

def run_realtime():
    feeds = [
        "https://news.google.com/rss/search?q=(factory+OR+industrial+OR+refinery+OR+semiconductor)+(fire+OR+explosion)+when:12h&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=(工廠+OR+廠房+OR+科技+OR+電子+OR+大樓+OR+中油+OR+台塑)+(火災+OR+爆炸+OR+起火)+when:12h&hl=zh-TW&gl=TW&ceid=TW:zh-tw"
    ]

    now = datetime.now()
    for url in feeds:
        try:
            res = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.content, "xml")
            for item in soup.find_all("item")[:30]:
                title = item.title.text
                link = item.link.text
                pub = item.pubDate.text if item.pubDate else ""

                if not is_real_incident(title): continue

                fp = incident_fingerprint(title)
                
                # 保險級防刷：判斷 24 小時內是否已發送過相似事件
                if fp in SEEN_EVENTS:
                    last_seen = datetime.fromisoformat(SEEN_EVENTS[fp])
                    if now - last_seen < timedelta(hours=24):
                        SUMMARY.add(fp)
                        print(f"跳過相似事件: {title[:20]}...")
                        continue

                flag = detect_country(title, link)
                channel = classify_channel(title)
                webhook = webhook_by_channel(channel)
                display_title = translate_to_zh(title) if flag != "🇹🇼" else title

                msg = f"{flag} **全球工業事故通報**\n🔥 分類：`{channel}`\n[{display_title}](<{link}>)\n🕒 時間：`{parse_time(pub)}`"
                
                requests.post(webhook, json={"content": msg}, timeout=10)
                SEEN_EVENTS[fp] = now.isoformat()
                SUMMARY.add(fp)
        except Exception as e:
            print(f"抓取錯誤: {e}")

    save_seen(SEEN_EVENTS)
    save_set(SUMMARY_FILE, SUMMARY)

def run_daily_summary():
    if not SUMMARY: return
    msg = f"🗞 **24h 工業事故摘要**\n共 {len(SUMMARY)} 起已合併事故"
    requests.post(WEBHOOK_GENERAL, json={"content": msg}, timeout=10)
    SUMMARY.clear()
    save_set(SUMMARY_FILE, SUMMARY)

if __name__ == "__main__":
    mode = os.getenv("MODE", "realtime")
    if mode == "summary":
        run_daily_summary()
    else:
        run_realtime()
