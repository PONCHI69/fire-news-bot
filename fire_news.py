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

def fetch_and_filter(rss_url, prefix):
    """抓取並進行二次嚴格檢查，確保標題真的與火災/爆炸有關"""
    try:
        res = requests.get(rss_url)
        soup = BeautifulSoup(res.content, features="xml")
        
        # 這是我們認可的「真火警」關鍵字
        valid_keywords = ["火","洩漏", "爆炸", "氣爆", "火警", "火燒", "焚毀", "Fire", "Explosion"]
        # 這是我們要排除的「無關」關鍵字（例如：買氣爆炸、效能爆炸）
        exclude_keywords = ["買氣", "效能", "票房", "熱度", "股市"]
        
        for item in soup.find_all('item')[:10]:
            title = item.title.text
            link = item.link.text
            
            # 邏輯：必須包含 valid 中的字，且不能包含 exclude 中的字
            has_valid = any(k.lower() in title.lower() for k in valid_keywords)
            has_exclude = any(e in title for e in exclude_keywords)
            
            if has_valid and not has_exclude:
                send_to_discord(title, link, prefix)
    except Exception as e:
        print(f"抓取失敗: {e}")

if __name__ == "__main__":
    print("--- 啟動終極精準監測系統 ---")
    
    # 1. 台灣本地搜尋
    tw_url = "https://news.google.com/rss/search?q=火災+OR+爆炸+OR+火警+when:1h&hl=zh-TW&gl=TW&ceid=TW:zh-tw"
    fetch_and_filter(tw_url, "🇹🇼 **台灣即時火警**")
    
    # 2. 全球中文搜尋 (加強版：搜尋全球新聞但要求 Google 提供中文標題)
    # 使用當前時間 1 小時內的新聞
    global_url = "https://news.google.com/rss/search?q=Fire+OR+Explosion+when:1h&hl=zh-TW&gl=TW&ceid=TW:zh-tw"
    fetch_and_filter(global_url, "🌍 **全球重大警報**")
    
    print("--- 監測結束 ---")
