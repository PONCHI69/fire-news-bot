import requests
from bs4 import BeautifulSoup
import os
import re

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

# 用來記錄本輪已經發送過的核心關鍵字，防止重複
sent_news_events = []

def translate_to_chinese(text):
    """簡單的 Google 翻譯 API"""
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=zh-TW&dt=t&q={text}"
        res = requests.get(url)
        return res.json()[0][0][0]
    except:
        return text

def is_duplicate(title):
    """
    簡單的去重邏輯：檢查標題中是否包含已發送過的關鍵地點或名詞。
    例如：標題有「卡拉奇」且之前發過「卡拉奇」，就視為重複。
    """
    # 提取標題中的主要地名或名詞（簡單過濾 2-4 個字的名詞）
    # 這是一個基礎邏輯，可以根據需求調整
    keywords = re.findall(r'[\u4e00-\u9fa5]{2,4}', title)
    
    for word in keywords:
        if word in sent_news_events:
            return True
    
    # 如果是全新的新聞，將主要詞彙存入紀錄
    for word in keywords:
        if len(word) >= 2:
            sent_news_events.append(word)
    return False

def send_to_discord(title, link, prefix):
    """將訊息發送至 Discord"""
    # 在發送前檢查是否重複
    if is_duplicate(title):
        print(f"跳過重複新聞：{title}")
        return

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
        
        valid_keywords = ["火", "爆炸", "氣爆", "火警", "焚毀", "Fire", "Explosion", "Blast"]
        exclude_keywords = [
            "警告", "宣導", "提醒", "呼籲", "司法", "程序", "律師", "災民", "善後",
            "家", "屋", "House", "Garage", "Home", "Apartment", "Residential",
            "買氣", "效能", "股市", "個資", "秘密", "名單", "熱度", "雜草", "野草"
        ]
        
        for item in soup.find_all('item')[:20]: # 增加掃描數量確保不漏掉
            title = item.title.text
            link = item.link.text
            
            has_valid = any(k.lower() in title.lower() for k in valid_keywords)
            has_exclude = any(e.lower() in title.lower() for e in exclude_keywords)
            
            if has_valid and not has_exclude:
                display_title = translate_to_chinese(title) if is_global else title
                # 清除標題末尾的來源標籤（例如 - 自由時報），增加去重準確度
                clean_title = re.sub(r'\s-\s.*$', '', display_title)
                
                print(f"嘗試發送：{clean_title}")
                send_to_discord(clean_title, link, prefix)
                
    except Exception as e:
        print(f"失敗: {e}")

if __name__ == "__main__":
    print("--- 啟動去重翻譯監測系統 ---")
    
    # 1. 台灣與兩岸搜尋 (12小時內)
    tw_url = "https://news.google.com/rss/search?q=火災+OR+爆炸+OR+火警+when:12h&hl=zh-TW&gl=TW&ceid=TW:zh-tw"
    fetch_and_filter(tw_url, "🇹🇼 **台灣/兩岸即時火警**")
    
    # 2. 全球英文搜尋 (12小時內)
    global_url = "https://news.google.com/rss/search?q=Fire+OR+Explosion+when:12h&hl=en-US&gl=US&ceid=US:en"
    fetch_and_filter(global_url, "🌍 **全球重大警報 (自動翻譯)**", is_global=True)
    
    print("--- 監測結束 ---")
