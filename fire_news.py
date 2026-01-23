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

# 擴充地點與事故詞彙
FIRE_KEYWORDS = ["fire", "blaze", "火災", "火警", "起火", "燒毀", "救災", "鋰電池", "太陽能", "儲能", "失火"]
EXPLOSION_KEYWORDS = ["explosion", "爆炸", "氣爆", "洩漏", "噴出"]
FACILITY_KEYWORDS = [
    "factory", "plant", "mill", "refinery", "warehouse", "工廠", "廠房", "倉儲", "工業",
    "公司", "科技", "電子", "廠", "倉庫", "園區", "中心", "作業", "現場", "槽", "管", 
    "中油", "化工", "油庫", "電廠", "台塑", "回收", "石化", "煉油", "化學", "大樓", "變電所", "林園", "大林"
]
EXCLUDE_KEYWORDS = [
    "演練", "模擬", "演習", "實兵", "宣導", "訓練", "simulation", "drill", "exercise",
    "遊戲", "steam", "模擬器", "股市", "營收", "講座", "論壇", "研討會", "房市", "預防",
    "闖關", "活動"
]

# =========================
# 邏輯模組
# =========================
def event_key(title, link):
    return hashlib.sha256(f"{title}{link}".encode("utf-8")).hexdigest()

def is_duplicate(title, link):
    if not os.path.exists(SEEN_FILE): return False
    with open(SEEN_FILE, "r") as f:
        seen = f.read().splitlines()
    return event_key(title, link) in seen

def save_event(title, link):
    with open(SEEN_FILE, "a") as f:
        f.write(event_key(title, link) + "\n")

def check_match(title, is_global=False):
    t = title.lower()
    # 優先排除黑名單
    if any(k in t for k in EXCLUDE_KEYWORDS): return False
    
    # 判斷是否含有火災/爆炸動作
    has_event = any(k in t for k in FIRE_KEYWORDS + EXPLOSION_KEYWORDS)
    
    if is_global:
        # 國外新聞放寬：只要有事件動詞且不在黑名單就通過
        return has_event
    else:
        # 國內新聞：必須同時包含事件動詞與設施地點
        has_place = any(k in t for k in FACILITY_KEYWORDS)
        return has_event and has_place

def get_severity(title):
    t = title.lower()
    if any(k in t for k in ["dead", "killed", "fatal", "死亡", "身亡"]): return "🚨 重大傷亡"
    if any(k in t for k in ["injured", "受傷"]): return "⚠️ 有人受傷"
    if any(k in t for k in EXPLOSION_KEYWORDS): return "💥 發生爆炸"
    return "🔥 火警通報"

def parse_time(date_str):
    try:
        gmt = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %Z')
        tw = gmt + timedelta(hours=8)
        return tw.strftime('%Y-%m-%d %H:%M')
    except:
        return "未知時間"

def translate_to_zh(text):
    try:
        res = requests.get("https://translate.googleapis.com/translate_a/single",
                           params={"client": "gtx", "sl": "en", "tl": "zh-TW", "dt": "t", "q": text}, timeout=10)
        return res.json()[0][0][0]
    except:
        return "（翻譯失敗）"

# =========================
# 執行主程式
# =========================
def run_monitor():
    urls = [
        ("https://news.google.com/rss/search?q=(工廠+OR+廠房+OR+工業區+OR+化工+OR+科技+OR+電子+OR+公司)+(火災+OR+爆炸+OR+火警+OR+起火)+when:12h&hl=zh-TW&gl=TW&ceid=TW:zh-tw", "🏭工廠情報"),
        ("https://news.google.com/rss/search?q=(中油+OR+石化+OR+煉油+OR+台塑+OR+林園+OR+大林)+(火災+OR+爆炸+OR+起火)+when:12h&hl=zh-TW&gl=TW&ceid=TW:zh-tw", "🔥火警"),
        ("https://news.google.com/rss/search?q=(factory+OR+industrial+OR+refinery)+(fire+OR+explosion)+when:12h&hl=zh-TW&gl=TW&ceid=TW:zh-tw", "🌍全球火警")
    ]

    for rss_url, prefix in urls:
        try:
            res = requests.get(rss_url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.content, features="xml")
            
            # 建立分類旗標，確保標籤文字與 URLs 定義完全一致
            is_global = (prefix == "🌍全球火警")
            
            for item in soup.find_all('item')[:20]:
                title = item.title.text
                link = item.link.text
                pub_date = item.pubDate.text if item.pubDate else ""
                tw_time = parse_time(pub_date)

                # 傳入分類旗標決定過濾嚴格度
                if check_match(title, is_global) and not is_duplicate(title, link):
                    # 組合訊息前先計算嚴重程度
                    severity = get_severity(title)
                    display_title = title
                    
                    # 僅針對全球火警執行自動翻譯
                    if is_global:
                        translated = translate_to_zh(title)
                        display_title = f"{title}\n📝 翻譯: {translated}"
                    
                    # 組合最終訊息格式
                    message = (
                        f"{prefix}\n"
                        f"**【{severity}】**\n"
                        f"[{display_title}](<{link}>)\n"
                        f"🕒 原始發布時間 (TW): `{tw_time}`"
                    )
                    
                    requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
                    save_event(title, link)
        except Exception as e:
            print(f"錯誤: {e}")

if __name__ == "__main__":
    run_monitor()
