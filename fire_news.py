import requests
from bs4 import BeautifulSoup
import hashlib
import os

# =========================
# 基本設定與關鍵字
# =========================
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
SEEN_FILE = "seen_events.txt"  # 建議改回文字檔，在 GitHub Actions 存檔最穩定

FIRE_KEYWORDS = ["fire", "blaze", "火災", "火警", "起火", "燒毀","救災","鋰電池","太陽能","儲能","失火"]
EXPLOSION_KEYWORDS = ["explosion", "爆炸", "氣爆","噴出","洩漏"]
FACILITY_KEYWORDS = ["factory", "plant", "mill", "refinery", "warehouse", "工廠", "廠房", "倉儲", "工業", "公司", "科技", "電子", "廠","倉庫","園區","中心","作業","現場","槽","管"]
EXCLUDE_KEYWORDS = ["遊戲", "steam", "限免", "模擬器", "大亨", "缺工", "關稅", "股市", "講座", "論壇","內閣","選","金正恩","研討會","營收","房市"]

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
    # 必須包含 (火災 或 爆炸) 且 必須包含 (設施地點) 且 不能有 (黑名單)
    has_event = any(k in t for k in FIRE_KEYWORDS + EXPLOSION_KEYWORDS)
    has_place = any(k in t for k in FACILITY_KEYWORDS)
    has_exclude = any(k in t for k in EXCLUDE_KEYWORDS)
    return has_event and has_place and not has_exclude

def get_severity(title):
    # 簡單判斷嚴重程度
    if any(k in title for k in ["死", "killed", "dead", "fatal"]): return "🚨 重大傷亡"
    if any(k in title for k in ["傷", "injured"]): return "⚠️ 有人受傷"
    if any(k in title for k in EXPLOSION_KEYWORDS): return "💥 發生爆炸"
    return "🔥 火警通報"

# =========================
# 執行主程式
# =========================
def run_monitor():
    urls = [
        ("https://news.google.com/rss/search?q=\"工廠\"+(火災+OR+爆炸+OR+火警)+when:24h&hl=zh-TW&gl=TW&ceid=TW:zh-tw", "🏭 工業/工廠情報"),
        ("https://news.google.com/rss/search?q=(\"factory\"+OR+\"industrial\")+(fire+OR+explosion)+when:24h&hl=zh-TW&gl=TW&ceid=TW:zh-tw", "🌍 全球工業警報")
    ]

    for rss_url, prefix in urls:
        try:
            res = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(res.content, features="xml")
            for item in soup.find_all('item')[:10]:
                title = item.title.text
                link = item.link.text
                
                if check_match(title) and not is_duplicate(title, link):
                    severity = get_severity(title)
                    # 組合訊息
                    message = f"{prefix}\n**【{severity}】**\n[{title}](<{link}>)"
                    requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
                    save_event(title, link)
        except Exception as e:
            print(f"錯誤: {e}")

if __name__ == "__main__":
    run_monitor()
