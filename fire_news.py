import requests
from bs4 import BeautifulSoup
import os

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

def send_to_discord(title, link, prefix):
    payload = {"content": f"{prefix} 【{title}】\n🔗 {link}"}
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
    except:
        pass

def fetch_taiwan_news():
    """台灣新聞：嚴格過濾關鍵字，避免雜訊"""
    url = "https://news.google.com/rss/search?q=火災+OR+爆炸+OR+火警+when:1h&hl=zh-TW&gl=TW&ceid=TW:zh-tw"
    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.content, features="xml")
        keywords = ["火", "爆炸", "氣爆", "火警", "火燒"]
        for item in soup.find_all('item')[:5]:
            title = item.title.text
            if any(k in title for k in keywords):
                send_to_discord(title, item.link.text, "🇹🇼 **台灣即時火警**")
    except: pass

def fetch_global_news():
    """全球新聞：不二度過濾，保證國外重大消息一定出現"""
    # 使用中文搜尋全球新聞，這會強制 Google 尋找已被翻譯或中文媒體報導的國際火警
    url = "https://news.google.com/rss/search?q=火災+OR+爆炸+when:1h&hl=zh-TW&gl=TW&ceid=TW:zh-tw"
    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.content, features="xml")
        for item in soup.find_all('item')[:3]:
            # 只要是這個搜尋結果出來的，就直接發送
            send_to_discord(item.title.text, item.link.text, "🌍 **全球重大警報**")
    except: pass

if __name__ == "__main__":
    print("--- 啟動最穩定監測系統 ---")
    fetch_taiwan_news()
    fetch_global_news()
    print("--- 監測結束 ---")
