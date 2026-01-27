import requests
from bs4 import BeautifulSoup
import hashlib
import os
import re
import json
from datetime import datetime

WEBHOOK = os.getenv("DISCORD_WEBHOOK_GENERAL")
SEEN_FILE = "seen_events.json"
HEADERS = {"User-Agent": "Mozilla/5.0"}

FIRE = ["fire", "blaze", "火災", "火警", "起火", "失火"]
EXPLOSION = ["explosion", "爆炸", "氣爆"]
EXCLUDE = ["演練", "模擬", "演習", "訓練", "simulation", "drill"]

COUNTRY_MAP = {
    "japan": "🇯🇵",
    "us": "🇺🇸",
    "u.s.": "🇺🇸",
    "germany": "🇩🇪",
    "uk": "🇬🇧",
    "china": "🇨🇳",
    "taiwan": "🇹🇼"
}

# ---------- utils ----------

def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()

def normalize(title):
    t = title.lower()
    t = re.sub(r"\d+", "", t)
    t = re.sub(r"[^a-z\u4e00-\u9fff]", "", t)
    return t[:30]

def fingerprint(title):
    return sha(normalize(title))

def is_real(title):
    t = title.lower()
    if any(x in t for x in EXCLUDE):
        return False
    return any(x in t for x in FIRE + EXPLOSION)

def detect_country(text):
    t = text.lower()
    for k, f in COUNTRY_MAP.items():
        if k in t:
            return f
    return "🌍"

def load_seen():
    if not os.path.exists(SEEN_FILE):
        return {}
    with open(SEEN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_seen(data):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def translate(text):
    try:
        r = requests.get(
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
        return r.json()[0][0][0]
    except:
        return text

def send_message(content):
    requests.post(
        WEBHOOK,
        json={"content": content},
        timeout=10
    )

# ---------- main ----------

def run():
    feeds = [
        "https://news.google.com/rss/search?q=factory+fire+explosion&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=工廠+火災+爆炸&hl=zh-TW&gl=TW&ceid=TW:zh-tw"
    ]

    seen = load_seen()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    for feed in feeds:
        res = requests.get(feed, headers=HEADERS)
        soup = BeautifulSoup(res.content, "xml")

        for item in soup.find_all("item")[:20]:
            title = item.title.text
            link = item.link.text

            if not is_real(title):
                continue

            fp = fingerprint(title)
            flag = detect_country(title + link)
            show_title = title if flag == "🇹🇼" else translate(title)

            if fp not in seen:
                seen[fp] = {
                    "count": 1,
                    "time": now,
                    "title": show_title,
                    "link": link
                }

                msg = (
                    f"{flag} **工業事故通報**\n"
                    f"[{show_title}](<{link}>)\n"
                    f"🧠 此事件已整合 1 則新聞來源\n"
                    f"🕒 {now}"
                )
                send_message(msg)

            else:
                seen[fp]["count"] += 1

    save_seen(seen)

if __name__ == "__main__":
    run()
