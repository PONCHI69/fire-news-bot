import requests
from bs4 import BeautifulSoup
import hashlib
import os
import re
import json
from datetime import datetime, timedelta

# =========================
# Discord Webhook
# =========================
WEBHOOK_GENERAL = os.getenv("DISCORD_WEBHOOK_GENERAL")

SEEN_FILE = "seen_events.json"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# =========================
# 關鍵字設定
# =========================
FIRE = ["fire", "blaze", "火災", "火警", "起火", "失火"]
EXPLOSION = ["explosion", "爆炸", "氣爆"]
EXCLUDE = [
    "演練", "模擬", "演習", "訓練", "simulation", "drill", "exercise",
    "股市", "財報", "營收", "政策", "趨勢", "宣導"
]

COUNTRY_MAP = {
    "japan": "🇯🇵",
    "us": "🇺🇸",
    "u.s.": "🇺🇸",
    "america": "🇺🇸",
    "germany": "🇩🇪",
    "uk": "🇬🇧",
    "china": "🇨🇳",
    "taiwan": "🇹🇼"
}

# =========================
# 工具
# =========================
def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()

def load_seen():
    if not os.path.exists(SEEN_FILE):
        return {}
    with open(SEEN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_seen(data):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def normalize_title(title):
    """
    用於 fingerprint，刻意不翻譯，避免同事件被切裂
    """
    t = title.lower()
    t = re.sub(r"\d+", "", t)
    t = re.sub(r"[^a-z\u4e00-\u9fff]", "", t)
    return t[:30]

def fingerprint(title):
    return sha(normalize_title(title))

def is_real_incident(title):
    t = title.lower()
    if any(k in t for k in EXCLUDE):
        return False
    return any(k in t for k in FIRE + EXPLOSION)

def detect_country(title, link):
    text = (title + link).lower()
    for k, flag in COUNTRY_MAP.items():
        if k in text:
            return flag
    return "🌍"

def parse_time(pub):
    try:
        gmt = datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %Z")
        return (gmt + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")
    except:
        return "未知"

# =========================
# 翻譯（只在非台灣新聞使用）
# =========================
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
        return text

# =========================
# Discord 發送（Thread）
# =========================
def send_message(content, thread_id=None, thread_name=None):
    payload = {"content": content}
    if thread_id:
        payload["thread_id"] = thread_id
    if thread_name:
        payload["thread_name"] = thread_name

    r = requests.post(WEBHOOK_GENERAL, json=payload, timeout=10)
    r.raise_for_status()
    return r.json()

# =========================
# 主流程
# =========================
def run():
    feeds = [
        "https://news.google.com/rss/search?q=(factory+OR+industrial)+(fire+OR+explosion)+when:12h&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=(工廠+OR+廠房)+(火災+OR+爆炸)+when:12h&hl=zh-TW&gl=TW&ceid=TW:zh-tw"
    ]

    seen = load_seen()

    for url in feeds:
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.content, "xml")

        for item in soup.find_all("item")[:30]:
            title = item.title.text
            link = item.link.text
            pub = item.pubDate.text if item.pubDate else ""

            if not is_real_incident(title):
                continue

            fp = fingerprint(title)
            flag = detect_country(title, link)

            # 顯示用標題（非台灣才翻譯）
            display_title = title if flag == "🇹🇼" else translate_to_zh(title)

            # === 新事件 ===
            if fp not in seen:
                msg = (
                    f"{flag} **全球工業事故通報**\n"
                    f"[{display_title}](<{link}>)\n"
                    f"🕒 `{parse_time(pub)}`\n"
                    f"🧠 此事件已整合 1 則新聞來源"
                )

                resp = send_message(msg, thread_name=display_title[:80])
                thread_id = resp["thread"]["id"]

                seen[fp] = {
                    "thread_id": thread_id,
                    "count": 1,
                    "created": datetime.utcnow().isoformat()
                }

            # === 同事件後續 ===
            else:
                seen[fp]["count"] += 1
                count = seen[fp]["count"]

                msg = (
                    f"🔄 **事件更新**（第 {count} 則來源）\n"
                    f"[{display_title}](<{link}>)\n"
                    f"🕒 `{parse_time(pub)}`"
                )

                send_message(
                    msg,
                    thread_id=seen[fp]["thread_id"]
                )

    save_seen(seen)

# =========================
# 入口
# =========================
if __name__ == "__main__":
    run()
