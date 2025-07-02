import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API 設定
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    
    # 快取設定
    CACHE_EXPIRE_MINUTES = int(os.getenv("CACHE_EXPIRE_MINUTES", "30"))
    MAX_CACHE_SIZE = int(os.getenv("MAX_CACHE_SIZE", "1000"))
    
    # 爬蟲設定
    REQUEST_DELAY = int(os.getenv("REQUEST_DELAY", "1"))  # 減少延遲
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))      # 減少重試次數
    TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "15"))  # 減少超時時間
    
    # Selenium 設定
    WEBDRIVER_PATH = os.getenv("WEBDRIVER_PATH", "")
    HEADLESS_MODE = os.getenv("HEADLESS_MODE", "true").lower() == "true"
    
    # 目標網站列表
    TARGET_STORES = [
        "coolpc",      # 原價屋
        "synnex",      # 欣亞
        "momo",        # momo購物網
        "pchome",      # PChome線上購物
        "dtsource",    # 德源電腦
        "sunfar3c",    # 順發3C
        "tsung3c"      # 三井3C
    ]
    
    # User-Agent 列表
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    ] 