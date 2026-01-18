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
    try:
        # 模擬瀏覽器，增加 Google 翻譯成功率
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        res = requests.get(rss_url, headers=headers)
        soup = BeautifulSoup(res.content, features="xml")
        items = soup.find_all('item')[:5] 
        
        strict_keywords = ["火", "爆炸", "氣爆", "火警", "火燒", "焚毀", "Fire", "Explosion"]
        
        for item in items:
            title = item.title.text
            link = item.link.text
            if use_strict:
                if any(k.lower() in title.lower() for k in strict_keywords):
                    send_to_discord(title, link, prefix)
            else:
                send_to_discord(title, link, prefix)
    except Exception as e:
        print(f"抓取失敗: {e}")

if __name__ == "__main__":
    print("--- 啟動全方位精準監測系統 ---")
    
    # 1. 台灣本地媒體 (搜尋繁體中文)
    tw_url = "https://news.google.com/rss/search?q=火災+OR+爆炸+OR+火警+when:1h&hl=zh-TW&gl=TW&ceid=TW:zh-tw"
    fetch_news(tw_url, "🇹🇼 **台灣即時火警**")
    
    # 2. 全球新聞 (修正參數：強制由台灣端發起搜尋，以獲取中文翻譯結果)
    # 把 gl=US 改為 gl=TW，並保持搜尋英文關鍵字，這樣 Google 會嘗試幫你翻译國外頭條
    global_zh_url = "https://news.google.com/rss/search?q=Fire+OR+Explosion+when:1h&hl=zh-TW&gl=TW&ceid=TW:zh-tw"
    fetch_news(global_zh_url, "🌍 **全球重大警報(中譯)**", use_strict=False)
    
    print("--- 監測結束 ---")
