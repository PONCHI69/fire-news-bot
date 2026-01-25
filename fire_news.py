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
TECH = ["semiconductor", "electronics", "wafer", "半導體", "科技", "電子", "面板", "光電", "積體電路"]
BUILDING = ["building", "apartment", "skyscraper", "大樓", "商辦", "住宅", "公寓", "建築"]

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
EXCLUDE += ["稅收", "股價", "財報", "營收", "總統", "選戰", "政策", "趨勢", "熱情", "點燃蘋果","稅收政策"]
# =========================
# 核心邏輯
# =========================
def is_real_incident(title):
    t = title.lower()
    
    # 1. 優先排除：標題若包含任何政經或排除詞彙，直接淘汰
    if any(k in t for k in EXCLUDE):
        return False
        
    # 2. 真實性檢查：必須含有明確的火警詞彙
    has_event = any(k in t for k in FIRE + EXPLOSION)
    
    # 3. 語意排除：排除掉「點燃趨勢」、「點燃希望」等比喻用法
    is_metaphor = any(k in t for k in ["點燃蘋果", "點燃市場", "點燃趨勢"])
    
    # 4. 防火宣導排除
    is_prevention = any(k in t for k in ["防火", "預防", "宣導", "平安符"])
    
    return has_event and not is_metaphor and not is_prevention

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
    if any(k in t for k in TECH):
        return "TECH"      # 回傳新類別：科技
    if any(k in t for k in BUILDING):
        return "BUILDING"  # 回傳新類別：大樓
    return "GENERAL"

def webhook_by_channel(ch):
    return {
        "CHEMICAL": WEBHOOK_CHEMICAL,
        "ENERGY": WEBHOOK_ENERGY,
        "TECH": WEBHOOK_GENERAL,     # 暫時導向一般頻道，或新增專屬 Webhook
        "BUILDING": WEBHOOK_GENERAL, # 暫時導向一般頻道
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
        # 1. 全球來源 (英文)：掌握國際重大工業意外
        "https://news.google.com/rss/search?q=(factory+OR+industrial+OR+refinery+OR+semiconductor)+(fire+OR+explosion)+when:12h&hl=en&gl=US&ceid=US:en",
        
        # 2. 台灣來源 (中文)：精準監控國內廠房、科技廠、大樓火警
        "https://news.google.com/rss/search?q=(工廠+OR+廠房+OR+科技+OR+電子+OR+大樓+OR+中油+OR+台塑)+(火災+OR+爆炸+OR+起火)+when:12h&hl=zh-TW&gl=TW&ceid=TW:zh-tw"
    ]

    for url in feeds:
        try:
            # 加入 timeout 確保網路波動時程式不會卡死
            res = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.content, "xml")
            
            for item in soup.find_all("item")[:30]:
                title = item.title.text
                link = item.link.text
                pub = item.pubDate.text if item.pubDate else ""

                # 核心判斷：排除演習、模擬等非真實事故
                if not is_real_incident(title):
                    continue

                # 指紋辨識：避免中英文報導同一則新聞時重複通報
                fp = incident_fingerprint(title)
                if fp in SEEN:
                    SUMMARY.add(fp)
                    continue

                flag = detect_country(title, link)
                channel = classify_channel(title)
                webhook = webhook_by_channel(channel)

                # 翻譯邏輯：只有非台灣的新聞才執行翻譯，節省效能並保持國內新聞原汁原味
                display_title = translate_to_zh(title) if flag != "🇹🇼" else title

                msg = (
                    f"{flag} **全球工業事故通報**\n"
                    f"🔥 分類：`{channel}`\n"
                    f"[{display_title}](<{link}>)\n"
                    f"🕒 時間：`{parse_time(pub)}`"
                )

                send(webhook, msg)
                SEEN.add(fp)
                SUMMARY.add(fp)
        except Exception as e:
            print(f"抓取 RSS 發生錯誤 ({url}): {e}")

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
