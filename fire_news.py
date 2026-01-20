import requests
from bs4 import BeautifulSoup
import hashlib
import os
import sqlite3
from datetime import datetime

# =========================
# 基本設定
# =========================

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
DB_FILE = "events.db"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# =========================
# 關鍵字設定（全球通用）
# =========================

FIRE_KEYWORDS = ["fire", "blaze", "火災", "火警"]
EXPLOSION_KEYWORDS = ["explosion", "爆炸", "氣爆"]

FACILITY_KEYWORDS = [
    "factory", "plant", "mill", "refinery", "warehouse",
    "chemical", "steel", "oil", "gas", "power",
    "工廠", "廠房", "鋼廠", "煉油", "化工", "電廠"
]

REGION_RULES = {
    "East Asia": ["china", "taiwan", "japan", "korea", "內蒙古", "日本", "韓國"],
    "Southeast Asia": ["vietnam", "thailand", "malaysia", "indonesia", "越南", "印尼"],
    "Europe": ["germany", "france", "uk", "italy", "europe"],
    "North America": ["usa", "canada", "mexico"],
    "South Asia": ["india", "pakistan"],
    "Middle East": ["saudi", "iran", "iraq"]
}

SEVERITY_RULES = [
    (5, ["多人死亡", "at least", "killed", "dead", "fatal"]),
    (4, ["死亡", "身亡"]),
    (3, ["受傷", "injured", "wounded"]),
    (2, ["爆炸", "explosion"]),
    (1, ["火災", "fire", "blaze"]),
]
