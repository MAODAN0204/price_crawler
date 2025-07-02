import aiohttp
import asyncio
import random
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from app.config import Config
from app.models.product import Product
from app.utils.price_formatter import PriceFormatter

class BaseScraper(ABC):
    """基礎爬蟲抽象類別"""
    
    def __init__(self, store_name: str):
        self.store_name = store_name
        self.session: Optional[aiohttp.ClientSession] = None
        self.config = Config()
        self.price_formatter = PriceFormatter()
    
    async def __aenter__(self):
        """異步上下文管理器進入"""
        await self._create_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """異步上下文管理器退出"""
        await self._close_session()
    
    async def _create_session(self):
        """建立HTTP會話"""
        headers = {
            'User-Agent': random.choice(self.config.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        timeout = aiohttp.ClientTimeout(total=self.config.TIMEOUT_SECONDS)
        # 建立SSL和DNS容錯的連接器
        connector = aiohttp.TCPConnector(
            limit=10,
            ssl=False,  # 暫時禁用SSL驗證以避免連接問題
            ttl_dns_cache=300,  # DNS快取5分鐘
            use_dns_cache=True,
        )
        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=timeout,
            connector=connector
        )
    
    async def _close_session(self):
        """關閉HTTP會話"""
        if self.session:
            await self.session.close()
    
    async def _fetch_page(self, url: str, params: Optional[Dict] = None) -> Optional[str]:
        """獲取網頁內容"""
        if not self.session:
            await self._create_session()
        
        for attempt in range(self.config.MAX_RETRIES):
            try:
                # 隨機延遲以避免被封鎖
                if attempt > 0:
                    delay = random.uniform(1, self.config.REQUEST_DELAY * 2)
                    await asyncio.sleep(delay)
                
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        # 嘗試多種編碼方式來處理中文網站
                        try:
                            content = await response.text(encoding='utf-8')
                        except UnicodeDecodeError:
                            try:
                                content = await response.text(encoding='big5')
                            except UnicodeDecodeError:
                                try:
                                    content = await response.text(encoding='gb2312')
                                except UnicodeDecodeError:
                                    # 如果都失敗，使用錯誤處理模式
                                    content = await response.text(encoding='utf-8', errors='ignore')
                        return content
                    else:
                        print(f"HTTP {response.status} for {url}")
                        
            except Exception as e:
                print(f"Attempt {attempt + 1} failed for {url}: {str(e)}")
                if attempt == self.config.MAX_RETRIES - 1:
                    return None
        
        return None
    
    def _parse_html(self, html_content: str) -> BeautifulSoup:
        """解析HTML內容"""
        return BeautifulSoup(html_content, 'html.parser')
    
    def _extract_price(self, price_text: str) -> Optional[float]:
        """提取價格"""
        return self.price_formatter.extract_price(price_text)
    
    def _is_in_stock(self, stock_text: str) -> bool:
        """判斷是否有庫存"""
        if not stock_text:
            return False
        
        stock_text = stock_text.lower()
        out_of_stock_indicators = [
            '無庫存', '缺貨', '售完', '暫無', '預購', 
            'out of stock', 'sold out', 'unavailable'
        ]
        
        return not any(indicator in stock_text for indicator in out_of_stock_indicators)
    
    def _clean_product_name(self, name: str) -> str:
        """清理產品名稱"""
        if not name:
            return ""
        
        # 移除多餘的空格和特殊字符
        cleaned = ' '.join(name.split())
        
        # 移除常見的標籤
        unwanted_patterns = [
            r'\[.*?\]',  # 方括號內容
            r'\(.*?\)',  # 圓括號內容（選擇性）
            r'【.*?】',   # 中文書名號
        ]
        
        for pattern in unwanted_patterns:
            cleaned = re.sub(pattern, '', cleaned)
        
        return cleaned.strip()
    
    @abstractmethod
    async def search_products(self, product_name: str) -> List[Product]:
        """搜尋產品 - 由子類實作"""
        pass
    
    @abstractmethod
    def _build_search_url(self, product_name: str) -> str:
        """建立搜尋URL - 由子類實作"""
        pass
    
    @abstractmethod
    def _parse_product_list(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """解析產品列表 - 由子類實作"""
        pass 