import requests
from bs4 import BeautifulSoup
import os
import re

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
sent_news_events = []

def translate_to_chinese(text):
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=zh-TW&dt=t&q={text}"
        res = requests.get(url)
        return res.json()[0][0][0]
    except:
        return text

def is_duplicate(title):
    # 提取標題中的主要地名或事件名詞進行去重
    keywords = re.findall(r'[\u4e00-\u9fa5]{2,4}', title)
    for word in keywords:
        if word in sent_news_events: return True
    for word in keywords:
        if len(word) >= 2: sent_news_events.append(word)
    return False

def fetch_and_filter(rss_url, prefix, is_global=False):
    try:
        res = requests.get(rss_url)
        soup = BeautifulSoup(res.content, features="xml")
        
        # 1. 指定工業/工廠相關關鍵字 (必須包含其中之一)
        industry_keywords = [
            "廠", "工業", "工廠", "化工", "鋼鐵", "紡織", "食品廠", "物流", 
            "倉儲", "建築", "工地", "電子廠", "半導體", "運輸", "煉油", "園區",
            "機房", "作業員", "廠房", "機台", "商場", "購物中心", "Mall", 
            "Factory", "Plant", "Industrial", "Warehouse", "Construction"
        ]
        
        # 2. 嚴格排除清單 (包含這些直接刪除)
        exclude_keywords = [
            "票房", "電影", "老店", "火鍋", "餐廳", "民宅", "公寓", "住宅", 
            "機車", "停車場", "雜草", "野草", "宿舍", "司法", "警告", "宣導",
            "潤餅", "店鋪", "旅店", "行政", "消防隊長", "司法"
        ]
        
        for item in soup.find_all('item')[:25]:
            title = item.title.text
            link = item.link.text
            
            # 先檢查是否有工業/大型場所關鍵字
            is_industry = any(k.lower() in title.lower() for k in industry_keywords)
            # 再檢查是否含有排除關鍵字
            has_exclude = any(e.lower() in title.lower() for e in exclude_keywords)
            
            # 全球新聞先翻譯再判斷，準確度更高
            display_title = translate_to_chinese(title) if is_global else title
            
            # 邏輯：必須是工業相關，且不能在排除名單內
            if is_industry and not has_exclude:
                clean_title = re.sub(r'\s-\s.*$', '', display_title)
                if not is_duplicate(clean_title):
                    print(f"符合工業標準：{clean_title}")
                    send_to_discord(clean_title, link, prefix)
                
    except Exception as e:
        print(f"失敗: {e}")

def send_to_discord(title, link, prefix):
    payload = {"content": f"{prefix} 【{title}】\n🔗 {link}"}
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
    except:
        pass

if __name__ == "__main__":
    print("--- 啟動 [工業級] 火災監測系統 ---")
    tw_url = "https://news.google.com/rss/search?q=工廠+OR+廠房+OR+工業區+OR+爆炸+when:12h&hl=zh-TW&gl=TW&ceid=TW:zh-tw"
    fetch_and_filter(tw_url, "🏭 **工業/工廠火警報告**")
    
    global_url = "https://news.google.com/rss/search?q=Factory+fire+OR+Industrial+explosion+OR+Warehouse+fire+when:12h&hl=en-US&gl=US&ceid=US:en"
    fetch_and_filter(global_url, "🌍 **全球工業警報 (AI翻譯)**", is_global=True)
    print("--- 監測結束 ---")
