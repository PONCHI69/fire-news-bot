import requests
from bs4 import BeautifulSoup
import os

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

def send_to_discord(title, link, prefix):
    """通用發送工具"""
    payload = {"content": f"{prefix} 【{title}】\n🔗 {link}"}
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
    except:
        pass

def fetch_taiwan_all_media():
    """透過 Google News RSS 抓取全台灣所有媒體(自由、聯合、中時、ETtoday等)"""
    # 搜尋關鍵字：火災 OR 爆炸 OR 火警
    # hl=zh-TW & gl=TW 代表台灣繁體中文地區
    url = "https://news.google.com/rss/search?q=火災+OR+爆炸+OR+火警+when:1h&hl=zh-TW&gl=TW&ceid=TW:zh-tw"
    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.content, features="xml")
        items = soup.find_all('item')[:10] # 每次最多抓最新 10 則
        
        for item in items:
            # Google RSS 的標題通常是 "新聞標題 - 報社名稱"
            send_to_discord(item.title.text, item.link.text, "🇹🇼 **台灣媒體聯播**")
    except Exception as e:
        print(f"台灣新聞抓取失敗: {e}")

def fetch_google_global():
    """抓取全球重大英文新聞 (最即時的國際消息)"""
    url = "https://news.google.com/rss/search?q=Fire+OR+Explosion+when:1h&hl=en-US&gl=US&ceid=US:en"
    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.content, features="xml")
        items = soup.find_all('item')[:3] # 國際大新聞抓前 3 則即可
        for item in items:
            send_to_discord(item.title.text, item.link.text, "🌍 **全球重大警報**")
    except Exception as e:
        print(f"全球新聞抓取失敗: {e}")

if __name__ == "__main__":
    print("--- 啟動全方位火災監測系統 ---")
    fetch_taiwan_all_media()
    fetch_google_global()
    print("--- 監測結束 ---")
