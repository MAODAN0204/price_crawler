#!/usr/bin/env python3
"""PChome 24h購物網爬蟲模組"""

import re
import json
import logging
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, quote
import aiohttp
from bs4 import BeautifulSoup

from app.models.product import Product
from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class PChomeScraper(BaseScraper):
    """PChome 24h購物網爬蟲"""
    
    def __init__(self):
        super().__init__("PChome 24h")
        self.base_url = "https://24h.pchome.com.tw"
        self.search_url = f"{self.base_url}/search"
    
    def _build_search_url(self, product_name: str) -> str:
        """建立搜尋URL"""
        return f"{self.search_url}/?q={quote(product_name)}"
    
    async def search_products(self, product_name: str, max_results: int = 50, standalone_only: bool = False, **kwargs) -> List[Product]:
        """搜尋產品"""
        try:
            logger.info(f"PChome搜尋: {product_name} (standalone_only={standalone_only})")
            
            search_url = self._build_search_url(product_name)
            logger.info(f"PChome搜尋URL: {search_url}")
            
            html = await self._fetch_page(search_url)
            if not html:
                logger.error("PChome無法獲取網頁內容")
                return []
            
            logger.info(f"PChome頁面長度: {len(html)} 字符")
            
            soup = self._parse_html(html)
            product_data_list = self._parse_product_list(soup, standalone_only)
            
            products = []
            for product_data in product_data_list:
                try:
                    product = Product(**product_data)
                    products.append(product)
                except Exception as e:
                    logger.error(f"PChome創建Product物件失敗: {e}")
                    continue
            
            logger.info(f"PChome成功解析 {len(products)} 個產品")
            return products[:max_results]
                    
        except Exception as e:
            logger.error(f"PChome搜尋失敗: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _parse_product_list(self, soup: BeautifulSoup, standalone_only: bool = False) -> List[Dict[str, Any]]:
        """解析產品列表"""
        products = []
        
        try:
            # PChome的產品可能在JavaScript中動態載入
            product_containers = soup.find_all('div', class_=['prod_info', 'item-container', 'prod-item'])
            
            if not product_containers:
                product_containers = soup.find_all('div', attrs={'data-id': True})
            
            if not product_containers:
                product_links = soup.find_all('a', href=re.compile(r'/prod/|/item/'))
                for link in product_links:
                    container = link.find_parent('div')
                    if container:
                        product_containers.append(container)
            
            logger.info(f"PChome找到 {len(product_containers)} 個產品容器")
            
            for container in product_containers:
                product_data = self._parse_product_container(container, standalone_only)
                if product_data:
                    products.append(product_data)
            
            return products
            
        except Exception as e:
            logger.error(f"PChome解析產品時發生錯誤: {e}")
            return []
    
    def _parse_product_container(self, container: BeautifulSoup, standalone_only: bool = False) -> Optional[Dict[str, Any]]:
        """解析單個產品容器"""
        try:
            name_elem = container.find(['h3', 'h4', 'h5', 'a'], class_=re.compile(r'name|title|prod'))
            if not name_elem:
                name_elem = container.find('a', href=re.compile(r'/prod/|/item/'))
            
            if not name_elem:
                return None
                
            product_name = name_elem.get_text(strip=True)
            if not product_name:
                return None
            
            # 檢查是否為組合包 - 在處理前檢查
            if standalone_only and self._is_bundle_product(product_name):
                logger.debug(f"PChome過濾組合包產品: {product_name}")
                return None
            
            product_url = ""
            link_elem = container.find('a', href=True)
            if link_elem:
                href = link_elem.get('href')
                if href.startswith('/'):
                    product_url = urljoin(self.base_url, href)
                elif href.startswith('http'):
                    product_url = href
            
            price = 0.0
            price_elem = container.find(['span', 'div', 'p'], class_=re.compile(r'price|cost|money'))
            if not price_elem:
                price_text_elem = container.find(text=re.compile(r'\$\d+|NT\$\d+|\d+元'))
                if price_text_elem:
                    price_elem = price_text_elem.parent
            
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price = self._extract_price(price_text) or 0.0
            
            in_stock = self._check_stock_status(container)
            
            image_url = None
            img_elem = container.find('img')
            if img_elem:
                src = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-original')
                if src:
                    if src.startswith('/'):
                        image_url = urljoin(self.base_url, src)
                    elif src.startswith('http'):
                        image_url = src
            
            product_name = self._clean_product_name(product_name)
            
            # 檢查是否為組合商品
            is_bundle = self._is_bundle_product(product_name)
            
            return {
                "store": "PChome 24h",
                "product_name": product_name,
                "price": price,
                "url": product_url,
                "in_stock": in_stock,
                "image_url": image_url,
                "is_bundle": is_bundle
            }
            
        except Exception as e:
            logger.error(f"PChome解析產品容器時發生錯誤: {e}")
            return None
    
    def _check_stock_status(self, container: BeautifulSoup) -> bool:
        """檢查庫存狀態"""
        try:
            stock_indicators = container.find_all(text=re.compile(
                r'缺貨|售完|補貨中|暫停供應|停產|預購|無庫存|out.*stock|sold.*out|暫不供貨',
                re.IGNORECASE
            ))
            
            if stock_indicators:
                return False
            
            buy_button = container.find(['button', 'a'], class_=re.compile(r'buy|cart|purchase|btn'))
            if buy_button:
                button_text = buy_button.get_text(strip=True)
                if re.search(r'缺貨|補貨|售完|暫停', button_text):
                    return False
                if buy_button.get('disabled') or 'disabled' in buy_button.get('class', []):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"PChome檢查庫存狀態時發生錯誤: {e}")
            return True
    
    def _is_bundle_product(self, product_name: str) -> bool:
        """檢查是否為組合包產品"""
        try:
            product_name_lower = product_name.lower()
            
            # 組合包關鍵字
            bundle_keywords = [
                '組合包', '套組', '套裝', '組合', '套餐', '大組包',
                '加購', '搭配', '含', '附', '贈',
                '組合價', '套餐價', '加贈', '贈送',
                '限量組合', '特惠組合', '超值組合', '精選組合',
                'combo', 'bundle', 'set', 'package',
                '買送', '購送', '送', '加1元多1件',
                '第二件', '2件', '兩件', '三件', '四件', '五件',
                '整組', '全套', '完整組合', '優惠組', '超值組',
                '電競機', '電腦主機', '整機', '桌機', '桌上型電腦',
                '主機板平台', '平台', '水冷獨顯', '獨顯水冷',
                '筆電', '筆記型電腦', 'laptop', 'notebook',
                '工作站', 'workstation', '迷你電腦', 'mini pc',
                '升級版', '豪華版', '旗艦版', '限定版',
                '合購', '搭機', '搭購', '限搭', '組裝價',
                '雙螢幕', '雙顯示器', '三螢幕', '多螢幕',
                '經濟組', '標準組', '進階組', '旗艦組',
                '入門組', '基本組', '完整組', '全配組',
                '豪華組', '精選組', '專業組', '商務組'
            ]
            
            # 檢查是否包含組合包關鍵字
            for keyword in bundle_keywords:
                if keyword in product_name_lower:
                    return True
            
            # 檢查是否包含多個產品指示詞
            multi_product_patterns = [
                r'\+\s*\w+',  # + 其他產品
                r'＋\s*\w+',  # ＋ 其他產品
                r'含\s*\w+',  # 含其他產品
                r'送\s*\w+',  # 送其他產品
                r'\d+件',     # X件
                r'\d+組',     # X組
                r'第\d+件',   # 第X件
                r'加購.*\d+元',  # 加購X元
                r'限時.*組合',   # 限時組合
                r'特價.*組合',   # 特價組合
            ]
            
            for pattern in multi_product_patterns:
                if re.search(pattern, product_name, re.IGNORECASE):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"PChome檢查組合包時發生錯誤: {e}")
            return False
    
    def _clean_product_name(self, name: str) -> str:
        """清理產品名稱"""
        if not name:
            return ""
        
        # 移除多餘的空白字符
        cleaned = re.sub(r'\s+', ' ', name.strip())
        
        # 移除特殊符號但保留必要的符號
        cleaned = re.sub(r'[^\w\s\-\+\(\)\[\]\/\.\,\:\;]', '', cleaned)
        
        return cleaned
 