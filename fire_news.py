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
# 擴充：加入大規模民宅相關詞彙
BUILDING = ["building", "apartment", "skyscraper", "大樓", "住宅", "公寓", "民宅", "社區", "neighborhood"]

# 排除雜訊
EXCLUDE = [
    "演練", "模擬", "演習", "訓練", "simulation", "drill", "exercise", "training",
    "股市", "政策", "調查", "委員會", "報告", "原因仍未確定", "起火成因", "宣導", 
    "housing", "房屋", "平安符", "點燃市場", "點燃蘋果"
]

FIRE_METAPHOR = ["under fire", "firestorm", "fiery debate", "political fire", "fire back"]

REAL_FIRE_CONTEXT = [
    "caught fire", "on fire", "burned", "burnt", "fire broke out", "fire erupted",
    "exploded", "blast", "detonated", "massive fire", "destroyed"
]

# 擴充：加入民宅設施關鍵字
FACILITY_KEYWORDS = [
    "factory", "plant", "refinery", "warehouse", "home", "house", "residential",
    "工廠", "廠房", "煉油廠", "食品廠", "餅乾", "民宅", "住宅", "社區"
]

COUNTRY_MAP = {
    "greece": "🇬🇷", "japan": "🇯🇵", "us": "🇺🇸", "u.s.": "🇺🇸", "america": "🇺🇸",
    "uk": "🇬🇧", "germany": "🇩🇪", "china": "🇨🇳", "taiwan": "🇹🇼", "brazil": "🇧🇷"
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
    """偵測標題中是否含有傷亡關鍵字"""
    combined_text = " ".join(titles).lower()
    # 匹配英文死傷或中文死傷
    if re.search(r"(\d+ (dead|kill|die|injure|victim)|(\d+)人(死|傷|亡|命))", combined_text):
        return "🚨 "
    return ""

# =========================
# 事故判斷與指紋提取
# =========================
def is_real_incident(title: str) -> bool:
    t = title.lower()
    if any(p in t for p in FIRE_METAPHOR): return False
    if any(k in t for k in EXCLUDE): return False
    
    has_event_word = any(k in t for k in FIRE + EXPLOSION)
    has_facility = any(k in t for k in FACILITY_KEYWORDS)
    has_real_context = (
        any(k in t for k in REAL_FIRE_CONTEXT)
        or any(k in t for k in ["火災", "起火", "失火", "爆炸", "氣爆", "燒毀"])
    )
    return has_event_word and has_facility and has_real_context

def extract_event_fingerprint(title):
    """提取事故核心特徵（移除變動數字以防範重複通報）"""
    t = title.lower()
    event_type = "fire" if any(k in t for k in FIRE) else "explosion"
    facility = next((k for k in FACILITY_KEYWORDS if k in t), "site")
    location = next((k for k in COUNTRY_MAP.keys() if k in t), "global")
    # 核心優化：移除所有數字，確保「300棟房屋」與「400棟房屋」指紋相同
    t_clean = re.sub(r"\d+", "", t)
    core = f"{location}-{facility}-{event_type}"
    return hashlib.sha256(core.encode("utf-8")).hexdigest()

# =========================
# 主流程
# =========================
def run_realtime():
    seen_events = load_seen()
    now = datetime.now()

    feeds = [
        # 原有工業搜尋
        "https://news.google.com/rss/search?q=(factory+OR+industrial+OR+refinery)+(fire+OR+explosion)+when:12h&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=(工廠+OR+廠房+OR+食品廠)+(火災+OR+爆炸)+when:12h&hl=zh-TW&gl=TW&ceid=TW:zh-tw",
        # 新增：大規模住宅火災搜尋
        "https://news.google.com/rss/search?q=(fire+OR+blaze)+(massive+OR+destroyed+OR+homes)+when:12h&hl=en&gl=US&ceid=US:en"
    ]

    event_pool = {}

    for url in feeds:
        try:
            res = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.content, "xml")

            for item in soup.find_all("item")[:40]:
                title = item.title.text
                if not is_real_incident(title): continue

                fp = extract_event_fingerprint(title)
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
            print(f"RSS 讀取錯誤: {e}")

    sent = 0
    for fp, data in event_pool.items():
        # 選擇中間長度的標題作為代表
        main_title = sorted(data["titles"], key=len)[len(data["titles"]) // 2]
        
        # 功能：偵測傷亡警報標記
        alert_prefix = detect_casualties(data["titles"])
        
        flag = detect_country(main_title)
        channel = classify_channel(main_title)
        webhook = webhook_by_channel(channel)

        is_chinese = bool(re.search(r"[\u4e00-\u9fff]", main_title))
        display_title = (
            main_title if is_chinese 
            else f"{main_title}\n（{translate_to_zh(main_title)}）"
        )

        # 功能：產生多來源簡化清單 (顯示前3則)
        others = data["titles"][1:4]
        source_list = "\n".join([f"• {t[:40]}..." for t in others])
        source_info = f"\n\n🔗 **相關報導**：\n{source_list}" if others else ""

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

    if sent == 0:
        requests.post(
            WEBHOOK_GENERAL,
            json={"content": "✅ **系統監測正常**\n系統設定的前 12 個小時內，無新增重大災情新聞。"},
            timeout=10,
        )

    save_seen(seen_events)

if __name__ == "__main__":
    run_realtime()
