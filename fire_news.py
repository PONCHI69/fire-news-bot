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

FIRE_KEYWORDS = ["fire", "blaze", "火災", "火警", "起火", "燒毀", "救災", "鋰電池", "太陽能", "儲能", "失火"]
EXPLOSION_KEYWORDS = ["explosion", "爆炸", "氣爆", "噴出", "洩漏"]
FACILITY_KEYWORDS = [
    "factory", "plant", "mill", "refinery", "warehouse", "工廠", "廠房", "倉儲", "工業",
    "公司", "科技", "電子", "廠", "倉庫", "園區", "中心", "作業", "現場", "槽", "管", 
    "中油", "化工", "油", "電廠", "台塑", "回收", "石化", "煉油", "化學", "大樓"
]
EXCLUDE_KEYWORDS = ["遊戲", "steam", "限免", "模擬器", "大亨", "缺工", "關稅", "股市", "講座", "論壇", "內閣", "選", "金正恩", "研討會", "營收", "房市"]

# =========================
# 邏輯模組
# =========================
def is_duplicate(title, link):
    key = hashlib.sha256(f"{title}{link}".encode("utf-8")).hexdigest()
    if not os.path.exists(SEEN_FILE):
        return False
    with open(SEEN_FILE, "r") as f:
        seen = f.read().splitlines()
    return key in seen

def save_event(title, link):
    key = hashlib.sha256(f"{title}{link}".encode("utf-8")).hexdigest()
    with open(SEEN_FILE, "a") as f:
        f.write(key + "\n")

def check_match(title):
    t = title.lower()
    has_event = any(k in t for k in FIRE_KEYWORDS + EXPLOSION_KEYWORDS)
    has_place = any(k in t for k in FACILITY_KEYWORDS)
    has_exclude = any(k in t for k in EXCLUDE_KEYWORDS)
    return has_event and has_place and not has_exclude

def get_severity(title):
    if any(k in title for k in ["死", "killed", "dead", "fatal"]): return "🚨 重大傷亡"
    if any(k in title for k in ["傷", "injured"]): return "⚠️ 有人受傷"
    if any(k in title for k in EXPLOSION_KEYWORDS): return "💥 發生爆炸"
    return "🔥 火警通報"

def parse_time(date_str):
    # 將 RSS 的 GMT 時間轉換為台灣時間 (UTC+8)
    try:
        # 格式範例: Fri, 23 Jan 2026 15:00:00 GMT
        gmt_time = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %Z')
        tw_time = gmt_time + timedelta(hours=8)
        return tw_time.strftime('%Y-%m-%d %H:%M')
    except:
        return "未知時間"

# =========================
# 執行主程式
# =========================
def run_monitor():
    urls = [
        ("https://news.google.com/rss/search?q=(工廠+OR+廠房+OR+石化+OR+工業區+OR+化工+OR+廠+OR+科技+OR+電子+OR+中油)+(火災+OR+爆炸+OR+火警+OR+起火)+when:24h&hl=zh-TW&gl=TW&ceid=TW:zh-tw", "🏭 工業/工廠情報"),
        ("https://news.google.com/rss/search?q=(factory+OR+industrial+OR+refinery)+(fire+OR+explosion)+when:24h&hl=zh-TW&gl=TW&ceid=TW:zh-tw", "🌍 全球工業警報")
    ]

    for rss_url, prefix in urls:
        try:
            res = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            soup = BeautifulSoup(res.content, features="xml")
            items = soup.find_all('item')
            
            for item in items[:15]:
                title = item.title.text
                link = item.link.text
                pub_date = item.pubDate.text if item.pubDate else ""
                tw_time_str = parse_time(pub_date)
                
                if check_match(title) and not is_duplicate(title, link):
                    severity = get_severity(title)
                    # 組合訊息：加入時間戳記 (使用 Discord 的程式碼區塊語法讓時間更顯眼)
                   message = (
                       f"{prefix}\n"
                       f"**【{severity}】**\n"
                       f"[{title}](<{link}>)\n"
                       f"🕒 原始發布時間 (TW): `{tw_time_str}`"
                    )
