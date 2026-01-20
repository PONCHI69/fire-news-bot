import requests
from bs4 import BeautifulSoup
import hashlib
import os
from typing import List

# ========================
# 設定區
# ========================
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
SEEN_FILE = "seen_events.txt"

# ========================
# 事件去重模組 (記錄已發送過的新聞)
# ========================
class EventDeduplicator:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.seen = self._load_seen()

    def _load_seen(self) -> set:
        if not os.path.exists(self.filepath):
            return set()
        with open(self.filepath, "r") as f:
            return set(line.strip() for line in f)

    def is_duplicate(self, title: str, link: str) -> bool:
        # 建立唯一指紋
        key = hashlib.sha256(f"{title}{link}".encode("utf-8")).hexdigest()
        if key in self.seen:
            return True
        self.seen.add(key)
        with open(self.filepath, "a") as f:
            f.write(key + "\n")
        return False

# ========================
# 關鍵字比對模組 (嚴格過濾邏輯)
# ========================
class KeywordMatcher:
    def __init__(self, fire_keywords, place_keywords, exclude_keywords):
        self.fire_keywords = fire_keywords
        self.place_keywords = place_keywords
        self.exclude_keywords = exclude_keywords

    def match(self, text: str) -> bool:
        t = text.lower()
        # 1. 必須含有火災動詞
        has_fire = any(k in t for k in self.fire_keywords)
        # 2. 必須含有工業地點
        has_place = any(k in t for k in self.place_keywords)
        # 3. 絕對不能含有黑名單 (解決遊戲、講座雜訊)
        has_exclude = any(e in t for e in self.exclude_keywords)
        return has_fire and has_place and not has_exclude

# ========================
# 主程式
# ========================
def run_monitor():
    dedup = EventDeduplicator(SEEN_FILE)
    matcher = KeywordMatcher(
        fire_keywords=["火災", "火警", "爆炸", "氣爆", "起火", "燒毀", "救災", "fire", "explosion"],
        place_keywords=["廠", "工業", "倉庫", "園區", "廠房", "倉儲", "factory", "warehouse"],
        exclude_keywords=["遊戲", "steam", "限免", "大亨", "模擬器", "缺工", "關稅", "股市", "招募", "講座", "論壇", "研討會", "法說"]
    )

    urls = [
        ("https://news.google.com/rss/search?q=\"工廠\"+(火災+OR+爆炸+OR+火警)+when:12h&hl=zh-TW&gl=TW&ceid=TW:zh-tw", "🏭 **工業/工廠火警報告**"),
        ("https://news.google.com/rss/search?q=(\"factory\"+OR+\"industrial\")+(fire+OR+explosion)+when:12h&hl=zh-TW&gl=TW&ceid=TW:zh-tw", "🌍 **全球工業警報 (AI翻譯)**")
    ]

    for rss_url, prefix in urls:
        try:
            res = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(res.content, features="xml")
            for item in soup.find_all('item')[:15]:
                title = item.title.text
                link = item.link.text
                
                # 過濾並去重
                if matcher.match(title) and not dedup.is_duplicate(title, link):
                    print(f"🚀 發送新事件: {title}")
                    payload = {"content": f"{prefix}\n**{title}**\n🔗 {link}"}
                    requests.post(DISCORD_WEBHOOK_URL, json=payload)
        except Exception as e:
            print(f"抓取失敗: {e}")

if __name__ == "__main__":
    run_monitor()
