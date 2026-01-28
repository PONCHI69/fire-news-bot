import requests
from bs4 import BeautifulSoup
import hashlib
import os
import re
from datetime import datetime, timedelta

# =========================
# Discord Webhook
# =========================
WEBHOOK_GENERAL = os.getenv("DISCORD_WEBHOOK_GENERAL")
HEADERS = {"User-Agent": "Mozilla/5.0"}

# =========================
# 關鍵字
# =========================
FIRE = ["fire", "blaze", "火災", "火警", "起火"]
EXPLOSION = ["explosion", "爆炸", "氣爆"]

EXCLUDE = [
    "演練", "演習", "訓練", "simulation", "drill",
    "股市", "財報", "政策", "宣導"
]

CAUSE_PATTERNS = {
    "⚡ 電氣系統": ["electrical", "short circuit", "配電", "電線"],
    "🧯 瓦斯／氣體": ["gas leak", "瓦斯", "氣體洩漏"],
    "⚙️ 設備故障": ["equipment failure", "設備故障"],
    "👤 人為操作": ["human error", "操作不當"],
}

COUNTRY_MAP = {
    "japan": "🇯🇵",
    "china": "🇨🇳",
    "taiwan": "🇹🇼",
    "us": "🇺🇸",
    "germany": "🇩🇪",
}

# =========================
# 工具
# =========================
def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()

def detect_country(text):
    t = text.lower()
    for k, v in COUNTRY_MAP.items():
        if k in t:
            return v
    return "🌍"

def is_incident(title):
    t = title.lower()
    if any(k in t for k in EXCLUDE):
        return False
    return any(k in t for k in FIRE + EXPLOSION)

# =========================
# 擴散搜尋
# =========================
def expand_search(keyword):
    q = keyword.replace(" ", "+")
    url = f"https://news.google.com/rss/search?q={q}+fire+OR+explosion&hl=en"
    res = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(res.content, "xml")
    titles = []
    for item in soup.find_all("item")[:8]:
        titles.append(item.title.text.lower())
    return titles

# =========================
# 原因推論
# =========================
def infer_cause(texts):
    score = {k: 0 for k in CAUSE_PATTERNS}
    for t in texts:
        for cause, kws in CAUSE_PATTERNS.items():
            if any(k in t for k in kws):
                score[cause] += 1

    ranked = sorted(score.items(), key=lambda x: x[1], reverse=True)
    if ranked[0][1] == 0:
        return "❓ 尚無足夠資訊研判原因"

    confidence = "高" if ranked[0][1] >= 3 else "中"
    return f"{ranked[0][0]}（信心：{confidence}，非官方）"

# =========================
# Discord Thread
# =========================
def post_and_create_thread(content, title):
    r = requests.post(WEBHOOK_GENERAL, json={"content": content}, timeout=10)
    r.raise_for_status()
    msg_id = r.json()["id"]

    thread_url = f"{WEBHOOK_GENERAL}/messages/{msg_id}/threads"
    r2 = requests.post(thread_url, json={"name": title[:90]}, timeout=10)
    r2.raise_for_status()
    return r2.json()["id"]

def post_thread(thread_id, content):
    url = f"{WEBHOOK_GENERAL}?thread_id={thread_id}"
    requests.post(url, json={"content": content}, timeout=10)

# =========================
# 主流程
# =========================
def run():
    feed = "https://news.google.com/rss/search?q=industrial+fire+OR+explosion&hl=en"
    res = requests.get(feed, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(res.content, "xml")

    events = {}

    for item in soup.find_all("item")[:30]:
        title = item.title.text
        link = item.link.text
        if not is_incident(title):
            continue

        fp = sha(title.lower())
        events.setdefault(fp, []).append((title, link))

    for ev in events.values():
        main_title, link = ev[0]
        flag = detect_country(main_title)

        expanded = expand_search(main_title)
        cause = infer_cause([main_title.lower()] + expanded)

        header = (
            f"{flag} **全球工業事故通報**\n"
            f"[{main_title}](<{link}>)\n"
            f"🧠 整合 `{len(ev) + len(expanded)}` 則來源"
        )

        thread_id = post_and_create_thread(header, main_title)

        detail = (
            f"🔍 **事故原因初步分析**\n"
            f"{cause}\n\n"
            f"📌 系統將持續追蹤更新"
        )
        post_thread(thread_id, detail)

if __name__ == "__main__":
    run()
