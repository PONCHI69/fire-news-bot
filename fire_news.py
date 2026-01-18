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

def fetch_news(rss_url, prefix, use_strict=True):
    """通用的抓取邏輯"""
    try:
        res = requests.get(rss_url)
        # 使用 lxml 解析
        soup = BeautifulSoup(res.content, features="xml")
        items = soup.find_all('item')[:5] 
        
        # 關鍵字清單
        strict_keywords = ["火", "爆炸", "氣爆", "火警", "火燒", "焚毀", "Fire", "Explosion"]
        
        for item in items:
            title = item.title.text
            link = item.link.text
            
            if use_strict:
                # 台灣版與全球版都檢查關鍵字
                if any(k.lower() in title.lower() for k in strict_keywords):
                    send_to_discord(title, link, prefix)
            else:
                # 如果不使用嚴格檢查，直接發送（通常用於已經搜尋過的 RSS）
                send_to_discord(title, link, prefix)
    except Exception as e:
        print(f"抓取失敗: {e}")

if __name__ == "__main__":
    print("--- 啟動全方位精準監測系統 ---")
    
    # 1. 台灣版 (搜尋中文關鍵字)
    tw_url = "https://news.google.com/rss/search?q=火災+OR+爆炸+OR+火警+when:1h&hl=zh-TW&gl=TW&ceid=TW:zh-tw"
    fetch_news(tw_url, "🇹🇼 **台灣即時火警**")
    
    # 2. 全球中文版 (使用搜尋參數直接過濾，不再二度過濾)
    # 我們在搜尋網址 q= 裡面已經放了 Fire OR Explosion，所以 Google 給的一定相關
    global_zh_url = "https://news.google.com/rss/search?q=Fire+OR+Explosion+when:1h&hl=zh-TW&gl=US&ceid=US:zh-tw"
    fetch_news(global_zh_url, "🌍 **全球重大警報(中譯)**", use_strict=False)
    
    print("--- 監測結束 ---")
