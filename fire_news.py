import requests
from bs4 import BeautifulSoup
import hashlib
import os
import re
import json
from datetime import datetime, timedelta

# =========================
# Webhooks
# =========================
WEBHOOK_GENERAL = os.getenv("DISCORD_WEBHOOK_GENERAL", "")
WEBHOOK_CHEMICAL = os.getenv("DISCORD_WEBHOOK_CHEMICAL", "")
WEBHOOK_ENERGY = os.getenv("DISCORD_WEBHOOK_ENERGY", "")

HEADERS = {"User-Agent": "Mozilla/5.0"}
SEEN_FILE = "seen_events.json"

# =========================
# 關鍵字
# =========================
FIRE = ["fire", "blaze", "火災", "火警", "起火", "失火"]
EXPLOSION = ["explosion", "爆炸", "氣爆"]

FALSE_FIRE_PHRASES = [
    "under fire",
    "political fire",
    "fire up",
    "fiery speech",
    "火力全開",
    "輿論抨擊",
]

EXCLUDE = [
    "演練", "模擬", "演習", "訓練", "simulation", "drill",
    "policy", "decision", "delay", "股市", "財報"
]

CHEMICAL = ["chemical", "petrochemical", "refinery", "石化", "化工", "煉油"]
ENERGY = ["power", "plant", "電廠", "變電所", "儲能", "鋰電池"]

COUNTRY_MAP = {
    "uk": "🇬🇧",
    "japan": "🇯🇵",
    "us": "🇺🇸",
    "china": "🇨🇳",
    "taiwan": "🇹🇼"
}

# =========================
# 工具
# =========================
def safe_post(webhook, payload):
    if not webhook or not webhook.startswith("https://"):
        print("⚠️ Webhook 未設定，略過送出")
        return None
    return requests.post(webhook, json=payload, timeout=10)

def load_seen():
    if not os.path.exists(SEEN_FILE):
        return {}
    with open(SEEN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_seen(data):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def translate_to_zh(text):
    try:
        r = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "auto", "tl": "zh-TW", "dt": "t", "q": text},
            timeout=8
        )
        return r.json()[0][0][0]
    except:
        return text

def is_real_fire(title):
    t = title.lower()
    if any(p in t for p in FALSE_FIRE_PHRASES):
        return False
    if any(e in t for e in EXCLUDE):
        return False
    return any(k in t for k in FIRE + EXPLOSION)

def classify_channel(title):
    t = title.lower()
    if any(k in t for k in CHEMICAL):
        return "CHEMICAL"
    if any(k in t for k in ENERGY):
        return "ENERGY"
    return "GENERAL"

def webhook_by_channel(ch):
    return {
        "CHEMICAL": WEBHOOK_CHEMICAL,
        "ENERGY": WEBHOOK_ENERGY,
        "GENERAL": WEBHOOK_GENERAL
    }.get(ch, WEBHOOK_GENERAL)

def fingerprint(title):
    core = re.sub(r"[^a-z\u4e00-\u9fff]", "", title.lower())
    return hashlib.sha256(core[:60].encode()).hexdigest()

# =========================
# 主流程
# =========================
def run():
    seen = load_seen()
    now = datetime.utcnow().isoformat()
    feeds = [
        "https://news.google.com/rss/search?q=(factory+OR+industrial+OR+refinery)+(fire+OR+explosion)+when:12h&hl=en&gl=US&ceid=US:en"
    ]

    events = {}

    for url in feeds:
        soup = BeautifulSoup(requests.get(url, headers=HEADERS).content, "xml")
        for item in soup.find_all("item")[:40]:
            title = item.title.text
            link = item.link.text

            if not is_real_fire(title):
                continue

            fp = fingerprint(title)
            if fp in seen:
                continue

            events.setdefault(fp, {"titles": [], "link": link})
            events[fp]["titles"].append(title)

    if not events:
        safe_post(WEBHOOK_GENERAL, {
            "content": "✅ **系統監測正常**\n過去 12 小時內無新增火災 / 爆炸事故。"
        })
        return

    for fp, data in events.items():
        main_title = data["titles"][0]
        zh = translate_to_zh(main_title)
        channel = classify_channel(main_title)
        webhook = webhook_by_channel(channel)

        content = (
            f"🔥 **全球工業事故通報**\n"
            f"分類：`{channel}`\n"
            f"{main_title}\n（{zh}）\n"
            f"🧠 此事件已整合 `{len(data['titles'])}` 則新聞來源\n"
            f"{data['link']}"
        )

        safe_post(webhook, {
            "content": content,
            "thread_name": zh[:80]
        })

        seen[fp] = now

    save_seen(seen)

if __name__ == "__main__":
    run()
