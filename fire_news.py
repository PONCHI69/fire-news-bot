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

# =========================
# 關鍵字設定
# =========================
FIRE = ["fire", "blaze", "火災", "火警", "起火", "失火", "大火", "延燒", "燒毀"]
EXPLOSION = ["explosion", "爆炸", "氣爆", "爆燃"]

CHEMICAL = ["chemical", "petrochemical", "refinery", "石化", "化工", "煉油"]
ENERGY = ["power", "plant", "電廠", "變電所", "儲能", "太陽能", "鋰電池"]
TECH = ["semiconductor", "electronics", "wafer", "半導體", "電子"]
BUILDING = ["building", "apartment", "skyscraper", "大樓", "住宅", "公寓", "民宅", "社區", "neighborhood", "home", "house"]

# 強化排除：過濾行政、法律、趨勢、非現場新聞
EXCLUDE = [
    "演練", "模擬", "演習", "訓練", "simulation", "drill", "exercise", "training",
    "股市", "政策", "調查", "委員會", "報告", "原因仍未確定", "起火成因", "宣導", 
    "housing", "房屋", "平安符", "點燃市場", "點燃蘋果", "order", "executive", "行政命令", "批准", "法案"
]

FIRE_METAPHOR = ["under fire", "firestorm", "fiery debate", "political fire", "fire back"]

REAL_FIRE_CONTEXT = [
    "caught fire", "on fire", "burned", "burnt", "fire broke out", "fire erupted",
    "exploded", "blast", "detonated", "massive fire", "destroyed"
]

FACILITY_KEYWORDS = [
    "factory", "plant", "refinery", "warehouse", "home", "house", "residential",
    "工廠", "廠房", "煉油廠", "食品廠", "餅乾", "民宅", "住宅", "社區", "nursery"
]

COUNTRY_MAP = {
    "greece": "🇬🇷", "japan": "🇯🇵", "us": "🇺🇸", "u.s.": "🇺🇸", "america": "🇺🇸",
    "uk": "🇬🇧", "germany": "🇩🇪", "china": "🇨🇳", "taiwan": "🇹🇼", "brazil": "🇧🇷",
    "norway": "🇳🇴", "trikala": "🇬🇷"
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
        res = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "auto", "tl": "zh-TW", "dt": "t", "q": text},
            timeout=10,
        )
        return res.json()[0][0][0]
    except: return text

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

def detect_casualties(titles):
    combined_text = " ".join(titles).lower()
    if re.search(r"(\d+ (dead|kill|die|injure|victim)|(\d+)人(死|傷|亡|命))", combined_text):
        return "🚨 "
    return ""

def is_real_incident(title: str) -> bool:
    t = title.lower()
    if any(p in t for p in FIRE_METAPHOR): return False
    if any(k in t for k in EXCLUDE): return False
    has_event_word = any(k in t for k in FIRE + EXPLOSION)
    has_facility = any(k in t for k in FACILITY_KEYWORDS)
    has_real_context = (
        any(k in t for k in REAL_FIRE_CONTEXT)
        or any(k in t for k in ["火災", "起火", "失火", "爆炸", "氣爆", "燒毀", "火警"])
    )
    return has_event_word and has_facility and has_real_context

def extract_event_fingerprint(title):
    """提取事故指紋：移除數字與噪音，強化跨次去重"""
    t = title.lower()
    # 移除標題結尾的媒體名稱 (通常在最後一個 - 或 | 之後)
    t = re.split(r' - | \| ', t)[0]
    location = next((k for k in COUNTRY_MAP.keys() if k in t), "global")
    facility = next((k for k in FACILITY_KEYWORDS if k in t), "site")
    # 移除所有數字避免指紋變動
    t_clean = re.sub(r"\d+", "", t)
    t_clean = re.sub(r"[^a-z\u4e00-\u9fff]", "", t_clean)
    core = f"{location}-{facility}-{t_clean[:10]}"
    return hashlib.sha256(core.encode("utf-8")).hexdigest()

# =========================
# 主流程
# =========================
def run_realtime():
    seen_events = load_seen()
    now = datetime.now()
    event_pool = {}

    feeds = [
        "https://news.google.com/rss/search?q=(factory+OR+industrial+OR+refinery)+(fire+OR+explosion)+when:12h&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=(工廠+OR+廠房+OR+食品廠)+(火災+OR+爆炸)+when:12h&hl=zh-TW&gl=TW&ceid=TW:zh-tw",
        "https://news.google.com/rss/search?q=(fire+OR+blaze)+(massive+OR+destroyed+OR+homes)+when:12h&hl=en&gl=US&ceid=US:en"
    ]

    for url in feeds:
        try:
            res = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.content, "xml")
            for item in soup.find_all("item")[:40]:
                title = item.title.text
                if not is_real_incident(title): continue

                fp = extract_event_fingerprint(title)
                # 跨次去重：如果檔案裡已經有這組指紋，代表之前發過了
                if fp in seen_events: continue

                if fp not in event_pool:
                    event_pool[fp] = {
                        "titles": [title],
                        "link": item.link.text,
                        "pub": item.pubDate.text if item.pubDate else "",
                    }
                else:
                    if title not in event_pool[fp]["titles"]:
                        event_pool[fp]["titles"].append(title)
        except Exception as e:
            print(f"RSS 錯誤: {e}")

    sent = 0
    for fp, data in event_pool.items():
        main_title_raw = data["titles"][0]
        # 過濾主標題尾部媒體名
        main_title = re.split(r' - | \| ', main_title_raw)[0]
        
        alert_prefix = detect_casualties(data["titles"])
        flag = detect_country(main_title)
        channel = classify_channel(main_title)
        webhook = webhook_by_channel(channel)

        is_chinese = bool(re.search(r"[\u4e00-\u9fff]", main_title))
        display_title = (
            main_title if is_chinese 
            else f"{main_title}\n（{translate_to_zh(main_title)}）"
        )

        # 相關報導白字邏輯：移除與主標題太相似的項目
        others = []
        main_norm = re.sub(r"[^a-zA-Z\u4e00-\u9fff]", "", main_title).lower()
        for t in data["titles"][1:5]:
            t_clean = re.split(r' - | \| ', t)[0]
            t_norm = re.sub(r"[^a-zA-Z\u4e00-\u9fff]", "", t_clean).lower()
            # 如果標題重合度不高才顯示
            if t_norm[:20] != main_norm[:20]:
                others.append(t_clean)

        source_info = f"\n\n🔗 **相關報導**：\n" + "\n".join([f"• {t[:50]}..." for t in others]) if others else ""

        msg = (
            f"{alert_prefix}{flag} **全球重大災情通報**\n"
            f"🔥 分類：`{channel}`\n"
            f"[{display_title}](<{data['link']}>)\n"
            f"🧠 本次掃描已整合 `{len(data['titles'])}` 則來源{source_info}\n"
            f"🕒 時間：`{data['pub']}`"
        )

        requests.post(webhook, json={"content": msg}, timeout=10)
        seen_events[fp] = now.isoformat()
        sent += 1

    # 修正心跳邏輯：如果掃描完畢完全沒有「新指紋」才發送
    if sent == 0:
        requests.post(
            WEBHOOK_GENERAL,
            json={"content": "✅ **系統監測正常**\n系統設定的前 12 個小時內，無新增重大災情新聞。"},
            timeout=10,
        )

    save_seen(seen_events)

if __name__ == "__main__":
    run_realtime()
