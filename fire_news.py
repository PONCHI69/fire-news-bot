import requests
from bs4 import BeautifulSoup
import os
import re

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

# 用來記錄本輪已發送事件的「特徵組合」
# 格式為: "地點+事件" (例如: "內蒙古+爆炸")
processed_events = set()

def translate_to_chinese(text):
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=zh-TW&dt=t&q={text}"
        res = requests.get(url)
        return res.json()[0][0][0]
    except:
        return text

def is_duplicate_event(title):
    """
    更強大的去重邏輯：
    1. 提取標題中的『地點』(如: 內蒙古, 桃園, 雅典)
    2. 提取標題中的『核心名詞』(如: 鋼鐵廠, 倉庫, 塑料廠)
    3. 如果這兩個組合同時出現過，則視為同一事件
    """
    # 提取地名 (2-4個中文字)
    locations = re.findall(r'[\u4e00-\u9fa5]{2,4}', title)
    # 提取核心名詞
    core_nouns = ["工廠", "廠房", "倉庫", "鋼鐵", "化工", "爆炸", "起火", "塑料", "物流"]
    
    found_loc = ""
    found_noun = ""
    
    for loc in locations:
        if len(loc) >= 2:
            found_loc = loc
            break
            
    for noun in core_nouns:
        if noun in title:
            found_noun = noun
            break
            
    # 如果同時找到地點與核心名詞，建立特徵值
    if found_loc and found_noun:
        event_fingerprint = f"{found_loc}_{found_noun}"
        if event_fingerprint in processed_events:
            return True
        processed_events.add(event_fingerprint)
    
    # 備用方案：如果標題超過 70% 相似，也視為重複 (這裡用簡單的長度檢查)
    return False

def fetch_and_filter(rss_url, prefix, is_global=False):
    try:
        res = requests.get(rss_url)
        soup = BeautifulSoup(res.content, features="xml")
        
        # 工業白名單
        industry_keywords = [
            "廠", "工業", "工廠", "化工", "鋼鐵", "紡織", "物流", "倉儲", 
            "電子廠", "半導體", "廠房", "機台", "倉庫", "Warehouse", "Factory"
        ]
        
        # 排除雜訊
        exclude_keywords = [
            "票房", "電影", "老店", "火鍋", "餐廳", "民宅", "公寓", "住宅", 
            "機車", "停車場", "雜草", "宿舍", "司法", "警告", "宣導", "申報", "留才"
        ]
        
        for item in soup.find_all('item')[:30]:
            title = item.title.text
            link = item.link.text
            
            # 全球新聞先翻譯，方便過濾
            display_title = translate_to_chinese(title) if is_global else title
            
            # 1. 檢查是否包含工業關鍵字
            is_industry = any(k.lower() in display_title.lower() for k in industry_keywords)
            # 2. 檢查是否含有排除關鍵字
            has_exclude = any(e.lower() in display_title.lower() for e in exclude_keywords)
            
            if is_industry and not has_exclude:
                # 3. 清理來源標籤
                clean_title = re.sub(r'\s-\s.*$', '', display_title)
                
                # 4. 核心去重檢查
                if not is_duplicate_event(clean_title):
                    print(f"發送新事件：{clean_title}")
                    send_to_discord(clean_title, link, prefix)
                else:
                    print(f"攔截重複事件：{clean_title}")
                
    except Exception as e:
        print(f"失敗: {e}")

def send_to_discord(title, link, prefix):
    payload = {"content": f"{prefix} 【{title}】\n🔗 {link}"}
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
    except:
        pass

if __name__ == "__main__":
    print("--- 啟動 [工業去重版] 監測系統 ---")
    tw_url = "https://news.google.com/rss/search?q=工廠+OR+廠房+OR+工業區+OR+爆炸+when:12h&hl=zh-TW&gl=TW&ceid=TW:zh-tw"
    fetch_and_filter(tw_url, "🏭 **工業/工廠火警報告**")
    
    global_url = "https://news.google.com/rss/search?q=Factory+fire+OR+Industrial+explosion+OR+Warehouse+fire+when:12h&hl=en-US&gl=US&ceid=US:en"
    fetch_and_filter(global_url, "🌍 **全球工業警報 (AI翻譯)**", is_global=True)
    print("--- 監測結束 ---")
