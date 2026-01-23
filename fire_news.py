import requests
from bs4 import BeautifulSoup
import hashlib
import os
from datetime import datetime, timedelta

# ... (保留您剛剛貼的關鍵字與翻譯函式部分) ...

def parse_time(date_str):
    try:
        # 將 RSS 的 GMT 轉為台灣時間 UTC+8
        gmt = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %Z')
        tw = gmt + timedelta(hours=8)
        return tw.strftime('%Y-%m-%d %H:%M')
    except:
        return "未知時間"

def run_monitor():
    urls = [
        ("https://news.google.com/rss/search?q=(工廠+OR+廠房+OR+石化+OR+工業區+OR+化工+OR+中油)+(火災+OR+爆炸+OR+火警)&hl=zh-TW&gl=TW&ceid=TW:zh-tw&when:24h", "🏭 工業/工廠情報"),
        ("https://news.google.com/rss/search?q=(factory+OR+industrial+OR+refinery)+(fire+OR+explosion)&hl=zh-TW&gl=TW&ceid=TW:zh-tw&when:24h", "🌍 全球工業警報")
    ]

    for rss_url, prefix in urls:
        try:
            res = requests.get(rss_url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.content, features="xml")
            for item in soup.find_all('item')[:10]:
                title = item.title.text
                link = item.link.text
                pub_date = item.pubDate.text if item.pubDate else ""
                tw_time = parse_time(pub_date)

                if check_match(title) and not is_duplicate(title, link):
                    severity = get_severity(title)
                    # 如果是英文新聞，自動加上中文翻譯
                    display_title = title
                    if prefix == "🌍 全球工業警報":
                        translated = translate_to_zh(title)
                        display_title = f"{title}\n📝 翻譯: {translated}"
                    
                    # 組合您最喜歡的清爽格式
                    message = (
                        f"{prefix}\n"
                        f"**【{severity}】**\n"
                        f"[{display_title}](<{link}>)\n"
                        f"🕒 原始發布時間 (TW): `{tw_time}`"
                    )
                    
                    requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
                    save_event(title, link)
        except Exception as e:
            print(f"錯誤: {e}")

if __name__ == "__main__":
    run_monitor()
