import requests
from bs4 import BeautifulSoup
import os

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

def send_to_discord(title, link, prefix):
    # 簡化格式，避免傳送冗長的 Google News 介紹文字
    payload = {"content": f"{prefix}\n**{title}**\n🔗 {link}"}
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
    except:
        pass

def fetch_and_filter(rss_url, prefix):
    try:
        # 模擬瀏覽器標頭，避免被 Google 阻擋
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(rss_url, headers=headers)
        soup = BeautifulSoup(res.content, features="xml")
        
        # 【白名單】標題必須包含這些核心火警字眼
        fire_keywords = ["火", "燒", "爆", "炸", "警", "災", "焚", "fire", "explosion"]
        # 【黑名單】完全排除遊戲、勞工、股市相關的標題
        exclude_keywords = ["遊戲", "steam", "限免", "大亨", "模擬器", "缺工", "關稅", "股市", "招募", "物流新聞"]

        for item in soup.find_all('item')[:15]:
            title = item.title.text
            link = item.link.text
            lower_title = title.lower()
            
            # 判斷邏輯：1. 必須有火災關鍵字 2. 絕對不能有雜訊關鍵字
            has_fire = any(k in lower_title for k in fire_keywords)
            has_exclude = any(e in lower_title for e in exclude_keywords)
            
            if has_fire and not has_exclude:
                send_to_discord(title, link, prefix)
                
    except Exception as e:
        print(f"抓取失敗: {e}")

if __name__ == "__main__":
    print("--- 啟動工廠火警精密監測系統 ---")
    
    # 1. 台灣與亞洲中文搜尋：針對「工廠火災/爆炸」進行精確組合搜尋
    tw_factory_url = "https://news.google.com/rss/search?q=工廠+(火災+OR+爆炸+OR+火警)+when:1h&hl=zh-TW&gl=TW&ceid=TW:zh-tw"
    fetch_and_filter(tw_factory_url, "🏭 **工業/工廠火警報告**")
    
    # 2. 全球英文來源中譯：搜尋 global 工廠事故
    global_factory_url = "https://news.google.com/rss/search?q=(factory+OR+industrial)+(fire+OR+explosion)+when:1h&hl=zh-TW&gl=TW&ceid=TW:zh-tw"
    fetch_and_filter(global_factory_url, "🌍 **全球工業警報 (AI翻譯)**")
    
    print("--- 監測結束 ---")
