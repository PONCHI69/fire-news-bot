import requests
from bs4 import BeautifulSoup
import os

# 從 GitHub Secrets 讀取 Webhook 網址
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

def send_to_discord(title, link, prefix):
    """將訊息發送至 Discord"""
    payload = {"content": f"{prefix} 【{title}】\n🔗 {link}"}
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
    except:
        pass

def fetch_and_filter(rss_url, prefix):
    """抓取並進行二次嚴格檢查，確保標題真的與火災/爆炸有關"""
    try:
        res = requests.get(rss_url)
        # RSS 是 XML 格式，使用 xml 解析器
        soup = BeautifulSoup(res.content, features="xml")
        
        # 1. 認可的「真火警」關鍵字
        valid_keywords = ["火", "洩漏", "爆炸", "氣爆", "火警", "火燒", "焚毀", "Fire", "Explosion"]
        
        # 2. 排除「形容詞」或「無關」關鍵字
        # 額外加入：秘密、隱私、名單 (預防洩漏類誤報)
        exclude_keywords = [
            "買氣", "效能", "票房", "熱度", "股市", "選情", "參選", 
            "樂透", "秘密", "隱私", "名單", "個資","模擬"
        ]
        
        for item in soup.find_all('item')[:10]:
            title = item.title.text
            link = item.link.text
            
            # 邏輯判斷：包含有效字眼 且 不包含排除字眼
            has_valid = any(k.lower() in title.lower() for k in valid_keywords)
            has_exclude = any(e in title for e in exclude_keywords)
            
            if has_valid and not has_exclude:
                print(f"符合條件並發送：{title}")
                send_to_discord(title, link, prefix)
                
    except Exception as e:
        print(f"抓取失敗 ({prefix}): {e}")

if __name__ == "__main__":
    print("--- 啟動終極精準監測系統 ---")
    
    # 1. 台灣本地搜尋 (中文媒體聯播)
    # hl=zh-TW, gl=TW 確保抓到台灣各大報社新聞
    tw_url = "https://news.google.com/rss/search?q=火災+OR+爆炸+OR+火警+when:1h&hl=zh-TW&gl=TW&ceid=TW:zh-tw"
    fetch_and_filter(tw_url, "🇹🇼 **台灣即時火警**")
    
    # 2. 全球英文搜尋 (國際第一手消息)
    # 改回 hl=en-US 以獲取美國、歐洲、日本等地原文報導，避免與台灣新聞重複
    global_url = "https://news.google.com/rss/search?q=Fire+OR+Explosion+when:1h&hl=en-US&gl=US&ceid=US:en"
    fetch_and_filter(global_url, "🌍 **全球重大警報**")
    
    print("--- 監測結束 ---")
