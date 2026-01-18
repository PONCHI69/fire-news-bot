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

def fetch_news(rss_url, prefix):
    """通用的抓取與嚴格過濾邏輯"""
    try:
        res = requests.get(rss_url)
        # 使用 lxml 解析 (請確保 main.yml 已加上 lxml)
        soup = BeautifulSoup(res.content, features="xml")
        items = soup.find_all('item')[:8] 
        
        # 嚴格過濾關鍵字，避免抓到「負擔爆炸」、「買氣火熱」等無關新聞
        strict_keywords = ["火", "爆炸", "氣爆", "火警", "火燒", "焚毀"]
        
        for item in items:
            title = item.title.text
            link = item.link.text
            
            # 只有標題包含火災關鍵字才發送
            if any(k in title for k in strict_keywords):
                send_to_discord(title, link, prefix)
    except Exception as e:
        print(f"抓取失敗: {e}")

if __name__ == "__main__":
    print("--- 啟動全方位精準監測系統 ---")
    
    # 1. 台灣版 (針對台灣媒體)
    tw_url = "https://news.google.com/rss/search?q=火災+OR+爆炸+OR+火警+when:1h&hl=zh-TW&gl=TW&ceid=TW:zh-tw"
    fetch_news(tw_url, "🇹🇼 **台灣即時火警**")
    
    # 2. 全球中文版 (搜尋全球大新聞，但由 Google 自動翻譯標題為中文)
    global_zh_url = "https://news.google.com/rss/search?q=Fire+OR+Explosion+when:1h&hl=zh-TW&gl=US&ceid=US:zh-tw"
    fetch_news(global_zh_url, "🌍 **全球重大警報(中譯)**")
    
    print("--- 監測結束 ---")
