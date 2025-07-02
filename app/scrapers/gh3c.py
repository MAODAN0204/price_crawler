#!/usr/bin/env python3
"""良興電子爬蟲模組"""

import re
import logging
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup

from app.models.product import Product
from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class GH3CScraper(BaseScraper):
    """良興電子爬蟲"""
    
    def __init__(self):
        super().__init__("良興電子")
        self.base_url = "https://www.gh3c.com.tw"
        self.search_url = f"{self.base_url}/index.php"
    
    def _build_search_url(self, product_name: str) -> str:
        """建立搜尋URL"""
        return f"{self.search_url}?app=search&act=index&keyword={quote(product_name)}"
    
    async def search_products(self, product_name: str, max_results: int = 50, **kwargs) -> List[Product]:
        """搜尋產品"""
        try:
            logger.info(f"良興電子搜尋: {product_name}")
            
            search_url = self._build_search_url(product_name)
            logger.info(f"良興電子搜尋URL: {search_url}")
            
            html = await self._fetch_page(search_url)
            if not html:
                logger.error("良興電子無法獲取網頁內容")
                return []
            
            logger.info(f"良興電子頁面長度: {len(html)} 字符")
            
            soup = self._parse_html(html)
            product_data_list = self._parse_product_list(soup)
            
            products = []
            for product_data in product_data_list:
                try:
                    product = Product(**product_data)
                    products.append(product)
                except Exception as e:
                    logger.error(f"良興電子創建Product物件失敗: {e}")
                    continue
            
            logger.info(f"良興電子成功解析 {len(products)} 個產品")
            return products[:max_results]
                    
        except Exception as e:
            logger.error(f"良興電子搜尋失敗: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _parse_product_list(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """解析產品列表"""
        products = []
        
        try:
            product_containers = soup.find_all('div', class_=re.compile(r'product-item|item-box|goods-item'))
            
            if not product_containers:
                product_containers = soup.find_all('li', class_=re.compile(r'product|item|goods'))
                
            if not product_containers:
                product_links = soup.find_all('a', href=re.compile(r'/product/|/goods/|/item/'))
                for link in product_links:
                    container = link.find_parent(['div', 'li'])
                    if container:
                        product_containers.append(container)
            
            if not product_containers:
                product_containers = soup.find_all('tr', class_=re.compile(r'product|item'))
                if not product_containers:
                    product_containers = soup.find_all('td', class_=re.compile(r'product|item'))
            
            logger.info(f"良興電子找到 {len(product_containers)} 個產品容器")
            
            for container in product_containers:
                product_data = self._parse_product_container(container)
                if product_data:
                    products.append(product_data)
            
            return products
            
        except Exception as e:
            logger.error(f"良興電子解析產品時發生錯誤: {e}")
            return []
    
    def _parse_product_container(self, container: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """解析單個產品容器"""
        try:
            name_elem = container.find(['h3', 'h4', 'h5', 'a'], class_=re.compile(r'title|name|product'))
            if not name_elem:
                name_elem = container.find('a', href=re.compile(r'/product/|/goods/|/item/'))
            if not name_elem:
                name_elem = container.find(['strong', 'b'])
            
            if not name_elem:
                return None
                
            product_name = name_elem.get_text(strip=True)
            if not product_name or len(product_name) < 3:
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
            price_elem = container.find(['span', 'div', 'td'], class_=re.compile(r'price|cost|money'))
            if not price_elem:
                price_text_elem = container.find(text=re.compile(r'\$\d+|NT\$\d+|\d+元|價格'))
                if price_text_elem:
                    price_elem = price_text_elem.parent
            
            if not price_elem:
                all_text = container.get_text()
                price_match = re.search(r'[\d,]+', all_text.replace(',', ''))
                if price_match:
                    try:
                        potential_price = float(price_match.group())
                        if 100 <= potential_price <= 1000000:
                            price = potential_price
                    except ValueError:
                        pass
            else:
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
            
            if not product_name or price <= 0:
                return None
            
            return {
                "store": "良興電子",
                "product_name": product_name,
                "price": price,
                "url": product_url,
                "in_stock": in_stock,
                "image_url": image_url
            }
            
        except Exception as e:
            logger.error(f"良興電子解析產品容器時發生錯誤: {e}")
            return None
    
    def _check_stock_status(self, container: BeautifulSoup) -> bool:
        """檢查庫存狀態"""
        try:
            stock_indicators = container.find_all(text=re.compile(
                r'缺貨|售完|補貨中|暫停供應|停產|預購|無庫存|out.*stock|sold.*out|現貨不足|暫時缺貨',
                re.IGNORECASE
            ))
            
            if stock_indicators:
                return False
            
            if container.find(class_=re.compile(r'soldOut|outStock|noStock|unavailable')):
                return False
            
            buy_button = container.find(['button', 'a', 'input'], class_=re.compile(r'buy|cart|purchase|order'))
            if buy_button:
                button_text = buy_button.get_text(strip=True)
                if re.search(r'缺貨|補貨|售完|暫停|無法購買|聯絡我們', button_text):
                    return False
                if buy_button.get('disabled') or 'disabled' in buy_button.get('class', []):
                    return False
            
            price_text = container.get_text()
            if re.search(r'詢價|電洽|來電詢問', price_text):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"良興電子檢查庫存狀態時發生錯誤: {e}")
            return True
    
 