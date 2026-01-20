import requests
from bs4 import BeautifulSoup
import os

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

def send_to_discord(title, link, prefix):
    # 【測試模式】：目前縮排已修正，僅會顯示在 GitHub Actions 日誌中
    print(f"--- 測試抓取成功 ---")
    print(f"標籤: {prefix}")
    print(f"標題: {title}")
    print(f"連結: {link}")
    print(f"------------------")
    # 下面這一行已註解，所以不會發送到 Discord
    # requests.post(DISCORD_WEBHOOK_URL, json={"content": f"{prefix}\n**{title}**\n🔗 {link}"})

def fetch_and_filter(rss_url, prefix):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(rss_url, headers=headers)
        soup = BeautifulSoup(res.content, features="xml")
        
        # 白名單：必須含有的火警字眼
        fire_keywords = ["火", "燒", "爆", "炸", "警", "災", "焚", "fire", "explosion"]
        # 黑名單：排除遊戲與雜訊（解決 Steam 遊戲問題）
        exclude_keywords = ["遊戲", "steam", "限免", "大亨", "模擬器", "缺工", "關稅", "股市", "招募", "物流新聞"]

        for item in soup.find_all('item')[:15]:
            title = item.title.text
            link = item.link.text
            lower_title = title.lower()
            
            has_fire = any(k in lower_title for k in fire_keywords)
            has_exclude = any(e in lower_title for e in exclude_keywords)
            
            # 同時符合條件才觸發 send_to_discord (目前的測試模式)
            if has_fire and not has_exclude:
                send_to_discord(title, link, prefix)
                
    except Exception as e:
        print(f"抓取失敗: {e}")

if __name__ == "__main__":
    print("--- 啟動精密過濾測試 (不發送 Discord) ---")
    
    # 台灣區精確搜尋
    tw_url = "https://news.google.com/rss/search?q=工廠+(火災+OR+爆炸+OR+火警)+when:8h&hl=zh-TW&gl=TW&ceid=TW:zh-tw"
    fetch_and_filter(tw_url, "🏭 **工業/工廠火警報告**")
    
    # 全球區精確搜尋
    global_url = "https://news.google.com/rss/search?q=(factory+OR+industrial)+(fire+OR+explosion)+when:8h&hl=zh-TW&gl=TW&ceid=TW:zh-tw"
    fetch_and_filter(global_url, "🌍 **全球工業警報 (AI翻譯)**")
    
    print("--- 測試結束 ---")
