import requests
from bs4 import BeautifulSoup
import os

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

def translate_to_chinese(text):
    """簡單的 Google 翻譯 API，將標題翻譯成中文"""
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=zh-TW&dt=t&q={text}"
        res = requests.get(url)
        # 翻譯結果在嵌套的 list 中：[[["翻譯後的文字", ...]]]
        return res.json()[0][0][0]
    except:
        return text  # 翻譯失敗則回傳原文

def send_to_discord(title, link, prefix):
    """將訊息發送至 Discord"""
    payload = {"content": f"{prefix} 【{title}】\n🔗 {link}"}
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
    except:
        pass

def fetch_and_filter(rss_url, prefix, is_global=False):
    """抓取並進行嚴格檢查與翻譯"""
    try:
        res = requests.get(rss_url)
        soup = BeautifulSoup(res.content, features="xml")
        
        # 1. 認可的「重大」火災關鍵字
        valid_keywords = ["火", "爆炸", "氣爆", "火警", "焚毀", "Fire", "Explosion", "Blast"]
        
        # 2. 嚴格排除清單：排除警告、家庭、瑣碎事物
        exclude_keywords = [
            "警告", "宣導", "提醒", "呼籲", "司法", "程序", "律師", "災民", "善後",
            "家", "屋", "House", "Garage", "Home", "Apartment", "Residential", # 排除家庭/民宅
            "買氣", "效能", "股市", "個資", "秘密", "名單", "熱度"
        ]
        
        for item in soup.find_all('item')[:15]:
            title = item.title.text
            link = item.link.text
            
            # 邏輯判斷
            has_valid = any(k.lower() in title.lower() for k in valid_keywords)
            has_exclude = any(e.lower() in title.lower() for e in exclude_keywords)
            
            if has_valid and not has_exclude:
                # 如果是全球警報，進行翻譯
                display_title = translate_to_chinese(title) if is_global else title
                print(f"發送：{display_title}")
                send_to_discord(display_title, link, prefix)
                
    except Exception as e:
        print(f"失敗: {e}")

if __name__ == "__main__":
    print("--- 啟動 AI 翻譯精準監測系統 ---")
    
    # 1. 台灣與兩岸搜尋
    tw_url = "https://news.google.com/rss/search?q=火災+OR+爆炸+OR+火警+when:1h&hl=zh-TW&gl=TW&ceid=TW:zh-tw"
    fetch_and_filter(tw_url, "🇹🇼 **台灣/兩岸即時火警**")
    
    # 2. 全球英文搜尋 (會自動翻譯成中文)
    global_url = "https://news.google.com/rss/search?q=Fire+OR+Explosion+when:1h&hl=en-US&gl=US&ceid=US:en"
    fetch_and_filter(global_url, "🌍 **全球重大警報 (自動翻譯)**", is_global=True)
    
    print("--- 監測結束 ---")
