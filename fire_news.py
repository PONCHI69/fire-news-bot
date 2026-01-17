import requests
from bs4 import BeautifulSoup
import os

# 從 GitHub Secrets 讀取網址
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

def send_to_discord(title, link, source):
    payload = {
        "content": f"🌍 **全球火災預警**\n【{title}】\n來源：{source}\n🔗 連結：{link}"
    }
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

def fetch_global_fire_news():
    # 使用 Google News RSS (關鍵字: Fire, 地點: 全球)
    # q=Fire+OR+Explosion 代表搜尋火災或爆炸
    # hl=en-US 代表語言為英文（全球資訊最快）
    rss_url = "https://news.google.com/rss/search?q=Fire+OR+Explosion+when:1h&hl=en-US&gl=US&ceid=US:en"
    
    try:
        response = requests.get(rss_url)
        # RSS 是 XML 格式，所以用 'xml' 解析器
        soup = BeautifulSoup(response.content, features="xml")
        
        # 抓取前 5 則最新新聞
        items = soup.find_all('item')[:5]
        
        if not items:
            print("目前全球暫無重大火災新聞更新。")
            return

        for item in items:
            title = item.title.text
            link = item.link.text
            source = item.source.text
            
            print(f"發送全球新聞：{title}")
            send_to_discord(title, link, source)
            
    except Exception as e:
        print(f"錯誤：{e}")

if __name__ == "__main__":
    fetch_global_fire_news()
