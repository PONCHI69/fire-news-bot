import requests
from bs4 import BeautifulSoup
import hashlib
import os
from datetime import datetime, timedelta
import sys

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
    "fire", "blaze", "火災", "火警", "起火", "燒毀", "失火", "救災",
    "鋰電池", "太陽能", "儲能"
]

EXPLOSION_KEYWORDS = [
    "explosion", "爆炸", "氣爆", "洩漏", "噴出"
]

FACILITY_KEYWORDS = [
    "factory", "plant", "mill", "refinery", "warehouse",
    "工廠", "廠房", "倉儲", "工業", "廠", "倉庫",
    "公司", "科技", "電子", "園區", "作業",
    "化工", "石化", "煉油", "油庫", "電廠",
    "中油", "台塑", "變電所", "大樓"
]

EXCLUDE_KEYWORDS = [
    "演練", "模擬", "演習", "訓練", "宣導", "預防",
    "simulation", "drill", "exercise",
    "遊戲", "steam", "模擬器",
    "股市", "營收", "房市", "論壇", "講座", "研討會",
    "活動"
]

# =========================
# 工具函式
# =========================
def ensure_seen_file():
    if not os.path.exists(SEEN_FILE):
        open(SEEN_FILE, "w").close()

def event_key(title, link):
    return hashlib.sha256(f"{title}{link}".encode("utf-8")).hexdigest()

def is_duplicate(title, link):
    ensure_seen_file()
    with open(SEEN_FILE, "r") as f:
        return event_key(title, link) in f.read().splitlines()

def save_event(title, link):
    ensure_seen_file()
    with open(SEEN_FILE, "a") as f:
        f.write(event_key(title, link) + "\n")

def check_match(title, is_global=False):
    t = title.lower()

    if any(k.lower() in t for k in EXCLUDE_KEYWORDS):
        return False

    has_event = any(k.lower() in t for k in FIRE_KEYWORDS + EXPLOSION_KEYWORDS)
    if not has_event:
        return False

    if is_global:
        return True

    return any(k.lower() in t for k in FACILITY_KEYWORDS)

def get_severity(title):
    t = title.lower()
    if any(k in t for k in ["dead", "killed", "fatal", "死亡", "身亡"]):
        return "🚨 重大傷亡"
    if any(k in t for k in ["injured", "受傷"]):
        return "⚠️ 有人受傷"
    if any(k in t for k in EXPLOSION_KEYWORDS):
        return "💥 發生爆炸"
    return "🔥 火警通報"

def parse_time(date_str):
    try:
        gmt = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z")
        tw = gmt + timedelta(hours=8)
        return tw.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "未知時間"

def translate_to_zh(text):
    try:
        res = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={
                "client": "gtx",
                "sl": "auto",
                "tl": "zh-TW",
                "dt": "t",
                "q": text
            },
            timeout=10
        )
        return res.json()[0][0][0]
    except Exception:
        return "（翻譯失敗）"

def send_to_discord(message):
    if not DISCORD_WEBHOOK_URL:
        print("❌ 未設定 DISCORD_WEBHOOK，已略過發送")
        return
    requests.post(DISCORD_WEBHOOK_URL, json={"content": message}, timeout=10)

# =========================
# 主流程
# =========================
def run_monitor():
    if not DISCORD_WEBHOOK_URL:
        print("⚠️ 警告：未設定 DISCORD_WEBHOOK，僅顯示 log")

    feeds = [
        (
            "https://news.google.com/rss/search?q=(工廠+OR+廠房+OR+工業區+OR+化工+OR+科技+OR+電子)+(火災+OR+爆炸+OR+火警+OR+起火)+when:12h&hl=zh-TW&gl=TW&ceid=TW:zh-tw",
            "🏭 工廠情報",
            False
        ),
        (
            "https://news.google.com/rss/search?q=(factory+OR+industrial+OR+refinery)+(fire+OR+explosion)+when:12h&hl=en&gl=US&ceid=US:en",
            "🌍 全球工業事故",
            True
        )
    ]

    for rss_url, prefix, is_global in feeds:
        print(f"🔍 抓取：{prefix}")
        try:
            res = requests.get(rss_url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.content, "xml")

            for item in soup.find_all("item")[:20]:
                title = item.title.text.strip()
                link = item.link.text.strip()
                pub_date = item.pubDate.text if item.pubDate else ""

                if not check_match(title, is_global):
                    continue
                if is_duplicate(title, link):
                    continue

                severity = get_severity(title)
                time_str = parse_time(pub_date)

                display_title = title
                if is_global:
                    display_title += f"\n📝 翻譯：{translate_to_zh(title)}"

                message = (
                    f"{prefix}\n"
                    f"**【{severity}】**\n"
                    f"[{display_title}](<{link}>)\n"
                    f"🕒 原始發布時間 (TW)：`{time_str}`"
                )

                send_to_discord(message)
                save_event(title, link)
                print(f"✅ 已通報：{title}")

        except Exception as e:
            print(f"❌ 抓取失敗：{e}")

# =========================
# 入口
# =========================
if __name__ == "__main__":
    run_monitor()
