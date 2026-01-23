import requests
from bs4 import BeautifulSoup
import hashlib
import os
from datetime import datetime, timedelta

# =========================
# 基本設定與關鍵字
# =========================
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
SEEN_FILE = "seen_events.txt"

FIRE_KEYWORDS = [
    "fire", "blaze", "火災", "火警", "起火", "燒毀", "救災",
    "鋰電池", "太陽能", "儲能", "失火"
]

EXPLOSION_KEYWORDS = ["explosion", "爆炸", "氣爆", "噴出", "洩漏"]

FACILITY_KEYWORDS = [
    "factory", "plant", "mill", "refinery", "warehouse",
    "工廠", "廠房", "倉儲", "工業", "化工", "石化", "煉油",
    "科技", "電子", "電廠", "園區", "中油", "台塑"
]

EXCLUDE_KEYWORDS = [
    "遊戲", "steam", "限免", "模擬", "大亨","演練",
    "缺工", "關稅", "股市", "講座", "論壇",
    "內閣", "選舉", "研討會", "營收", "房市"
]

HEADERS = {"User-Agent": "Mozilla/5.0"}

# =========================
# 去重處理
# =========================
def _event_key(title, link):
    return hashlib.sha256(f"{title}{link}".encode("utf-8")).hexdigest()

def is_duplicate(title, link):
    if not os.path.exists(SEEN_FILE):
        return False
    key = _event_key(title, link)
    with open(SEEN_FILE, "r") as f:
        return key in f.read().splitlines()

def save_event(title, link):
    key = _event_key(title, link)
    with open(SEEN_FILE, "a") as f:
        f.write(key + "\n")

# =========================
# 判斷邏輯
# =========================
def check_match(title):
    t = title.lower()
    has_event = any(k in t for k in FIRE_KEYWORDS + EXPLOSION_KEYWORDS)
    has_place = any(k in t for k in FACILITY_KEYWORDS)
    has_exclude = any(k in t for k in EXCLUDE_KEYWORDS)
    return has_event and has_place and not has_exclude

def get_severity(title):
    t = title.lower()
    if any(k in t for k in ["死", "killed", "dead", "fatal"]):
        return "🚨 重大傷亡"
    if any(k in t for k in ["傷", "injured"]):
        return "⚠️ 有人受傷"
    if any(k in t for k in EXPLOSION_KEYWORDS):
        return "💥 發生爆炸"
    return "🔥 火警通報"

def parse_time(date_str):
    try:
        gmt_time = datetime.strptime(
            date_str, "%a, %d %b %Y %H:%M:%S %Z"
        )
        tw_time = gmt_time + timedelta(hours=8)
        return tw_time.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "未知時間"

# =========================
# 主程式
# =========================
def run_monitor():
    urls = [
        (
            'https://news.google.com/rss/search?q='
            '(工廠+OR+廠房+OR+石化+OR+工業區+OR+化工+OR+科技+OR+電子)'
            '+(火災+OR+爆炸+OR+火警+OR+起火)+when:24h'
            '&hl=zh-TW&gl=TW&ceid=TW:zh-tw',
            "🏭 工業/工廠情報"
        ),
        (
            'https://news.google.com/rss/search?q='
            '(factory+OR+industrial+OR+refinery)'
            '+(fire+OR+explosion)+when:24h'
            '&hl=en-US&gl=US&ceid=US:en',
            "🌍 全球工業警報"
        )
    ]

    for rss_url, prefix in urls:
        try:
            res = requests.get(rss_url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.content, features="xml")
            items = soup.find_all("item")

            for item in items[:15]:
                title = item.title.text.strip()
                link = item.link.text.strip()
                pub_date = item.pubDate.text if item.pubDate else ""
                tw_time = parse_time(pub_date)

                if not check_match(title):
                    continue
                if is_duplicate(title, link):
                    continue

                severity = get_severity(title)

                message = (
                    f"{prefix}\n"
                    f"**【{severity}】**\n"
                    f"[{title}](<{link}>)\n"
                    f"🕒 原始發布時間 (TW): `{tw_time}`"
                )

                print(message)

                if DISCORD_WEBHOOK_URL:
                    requests.post(
                        DISCORD_WEBHOOK_URL,
                        json={"content": message},
                        timeout=10
                    )

                save_event(title, link)

        except Exception as e:
            print(f"[ERROR] RSS 讀取失敗: {e}")

# =========================
# 進入點
# =========================
if __name__ == "__main__":
    run_monitor()
