import requests
from bs4 import BeautifulSoup
import os  # 雲端版必備

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

def send_to_discord(title, link):
    payload = {"content": f"🔥 **偵測到火災相關新聞！**\n【{title}】\n{link}"}
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

def fetch_fire_news():
    url = "https://news.ltn.com.tw/list/breakingnews/society"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        news_list = soup.find('ul', class_='list').find_all('li')
        keywords = ["火", "爆炸", "氣爆", "火警"]
        for news in news_list:
            title_tag = news.find('h3')
            if title_tag:
                title = title_tag.text.strip()
                link = news.find('a')['href']
                if any(k in title for k in keywords):
                    send_to_discord(title, link)
        print("掃描完成")
    except Exception as e:
        print(f"錯誤：{e}")

if __name__ == "__main__":
    fetch_fire_news()
