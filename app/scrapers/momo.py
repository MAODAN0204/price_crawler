#!/usr/bin/env python3
"""momo購物網爬蟲模組"""

import re
import logging
import asyncio
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup

from app.models.product import Product
from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class MomoScraper(BaseScraper):
    """momo購物網爬蟲"""
    
    def __init__(self):
        super().__init__("momo購物網")
        self.base_url = "https://www.momoshop.com.tw"
        self.search_url = f"{self.base_url}/search/searchShop.jsp"
    
    def get_headers(self) -> Dict[str, str]:
        """獲取請求標頭，模擬真實瀏覽器"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.momoshop.com.tw/',
        }
    
    def _build_search_url(self, product_name: str) -> str:
        """建立搜尋URL"""
        return f"{self.search_url}?keyword={quote(product_name)}&_isFuzzy=0&searchType=1"
    
    async def search_products(self, product_name: str, max_results: int = 20, **kwargs) -> List[Product]:
        """搜尋產品"""
        try:
            logger.info(f"momo搜尋: {product_name}")
            
            search_url = self._build_search_url(product_name)
            logger.info(f"momo搜尋URL: {search_url}")
            
            # 增加延遲避免被封鎖
            await asyncio.sleep(1)
            
            html = await self._fetch_page(search_url)
            if not html:
                logger.error("momo無法獲取網頁內容")
                return []
            
            # 檢查是否被重定向到驗證頁面
            if 'robot' in html.lower() or 'captcha' in html.lower() or 'verify' in html.lower():
                logger.warning("momo檢測到機器人驗證頁面，暫時無法搜尋")
                return []
            
            logger.info(f"momo頁面長度: {len(html)} 字符")
            
            soup = BeautifulSoup(html, 'html.parser')
            products = await self._parse_product_list(soup, max_results)
            
            logger.info(f"momo成功解析 {len(products)} 個產品")
            return products
                    
        except Exception as e:
            logger.error(f"momo搜尋失敗: {e}")
            return []
    
    async def _parse_product_list(self, soup: BeautifulSoup, max_results: int) -> List[Product]:
        """解析產品列表"""
        products = []
        
        try:
            # 嘗試多種可能的產品容器選擇器
            selectors = [
                'li.goodsItemLi',
                'div.productInfoWrap', 
                'div.item-wrap',
                'div.prdListArea li',
                'ul.searchGoodsList li',
                'div.listArea li'
            ]
            
            product_containers = []
            for selector in selectors:
                containers = soup.select(selector)
                if containers:
                    product_containers = containers
                    logger.info(f"momo使用選擇器 '{selector}' 找到 {len(containers)} 個產品")
                    break
            
            if not product_containers:
                # 通過產品連結查找
                product_links = soup.find_all('a', href=re.compile(r'/goods/|/product/'))
                for link in product_links[:max_results]:
                    container = link.find_parent(['li', 'div'])
                    if container:
                        product_containers.append(container)
                
                logger.info(f"momo通過連結找到 {len(product_containers)} 個產品容器")
            
            for container in product_containers[:max_results]:
                try:
                    product = await self._parse_product_container(container)
                    if product:
                        products.append(product)
                except Exception as e:
                    logger.debug(f"momo解析單個產品失敗: {e}")
                    continue
            
            return products
            
        except Exception as e:
            logger.error(f"momo解析產品列表時發生錯誤: {e}")
            return []
    
    async def _parse_product_container(self, container) -> Optional[Product]:
        """解析單個產品容器"""
        try:
            # 尋找產品名稱
            name_elem = None
            name_selectors = [
                'h3.prdName',
                'p.prdName', 
                'a.prdName',
                '.productName',
                'h4.productName',
                '.goods_name'
            ]
            
            for selector in name_selectors:
                name_elem = container.select_one(selector)
                if name_elem:
                    break
            
            if not name_elem:
                # 嘗試通過連結找到名稱
                name_elem = container.find('a', href=re.compile(r'/goods/|/product/'))
            
            if not name_elem:
                return None
                
            product_name = name_elem.get_text(strip=True)
            if not product_name:
                return None
            
            # 獲取產品URL
            product_url = ""
            link_elem = container.find('a', href=True)
            if link_elem:
                href = link_elem.get('href')
                if href.startswith('/'):
                    product_url = urljoin(self.base_url, href)
                elif href.startswith('http'):
                    product_url = href
            
            # 獲取價格
            price = 0
            price_text = ""
            price_selectors = [
                '.price_box .cost',
                '.price .cost',
                '.prdPrice',
                '.productPrice'
            ]
            
            price_elem = None
            for selector in price_selectors:
                price_elem = container.select_one(selector)
                if price_elem:
                    break
            
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_match = re.search(r'[\d,]+', price_text.replace('$', '').replace(',', ''))
                if price_match:
                    try:
                        price = int(price_match.group().replace(',', ''))
                    except ValueError:
                        price = 0
            
            # 檢查庫存
            in_stock = await self._check_stock_status(container)
            
            # 獲取圖片
            image_url = ""
            img_elem = container.find('img')
            if img_elem:
                src = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-original')
                if src:
                    if src.startswith('/'):
                        image_url = urljoin(self.base_url, src)
                    elif src.startswith('http'):
                        image_url = src
            
            # 清理產品名稱
            product_name = self._clean_product_name(product_name)
            
            product = Product(
                name=product_name,
                price=price,
                price_text=price_text,
                url=product_url,
                image_url=image_url,
                description="",
                store="momo購物網",
                availability="有庫存" if in_stock else "缺貨"
            )
            
            return product
            
        except Exception as e:
            logger.debug(f"momo解析產品容器時發生錯誤: {e}")
            return None
    
    async def _check_stock_status(self, container) -> bool:
        """檢查庫存狀態"""
        try:
            # 檢查缺貨標識
            stock_indicators = container.find_all(text=re.compile(
                r'缺貨|售完|補貨中|暫停供應|停產|預購|無庫存|out.*stock|sold.*out|暫不供貨|現貨不足',
                re.IGNORECASE
            ))
            
            if stock_indicators:
                return False
            
            # 檢查CSS類名
            if container.find(class_=re.compile(r'soldOut|outStock|noStock')):
                return False
            
            # 檢查購買按鈕
            buy_button = container.find(['button', 'a'], class_=re.compile(r'addCart|buyNow|purchase'))
            if buy_button:
                button_text = buy_button.get_text(strip=True)
                if re.search(r'缺貨|補貨|售完|暫停|無法購買', button_text):
                    return False
                if buy_button.get('disabled') or 'disabled' in buy_button.get('class', []):
                    return False
            
            return True
            
        except Exception as e:
            logger.debug(f"momo檢查庫存狀態時發生錯誤: {e}")
            return True
    
    def _clean_product_name(self, name: str) -> str:
        """清理產品名稱"""
        # 移除多餘的空白
        name = re.sub(r'\s+', ' ', name.strip())
        
        # 移除momo特有的標記
        name = re.sub(r'【.*?】', '', name)  # 移除【】標記
        name = re.sub(r'\[.*?\]', '', name)  # 移除[]標記
        name = re.sub(r'★.*?★', '', name)  # 移除★標記
        name = re.sub(r'☆.*?☆', '', name)  # 移除☆標記
        name = re.sub(r'限時特價.*?$', '', name)  # 移除限時特價標記
        
        return name.strip()
    
    async def get_product_details(self, product_url: str) -> Dict[str, Any]:
        """獲取產品詳細資訊"""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers=self.get_headers()
            ) as session:
                async with session.get(product_url) as response:
                    if response.status != 200:
                        return {}
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    details = {}
                    
                    # 提取詳細規格
                    spec_section = soup.find(['div', 'table'], class_=re.compile(r'spec|specification|detail|info'))
                    if spec_section:
                        specs = {}
                        # momo的規格通常在表格中
                        spec_rows = spec_section.find_all(['tr', 'dt', 'li'])
                        for row in spec_rows:
                            text = row.get_text(strip=True)
                            if ':' in text or '：' in text:
                                separator = ':' if ':' in text else '：'
                                parts = text.split(separator, 1)
                                if len(parts) == 2:
                                    specs[parts[0].strip()] = parts[1].strip()
                        details['specifications'] = specs
                    
                    # 提取商品描述
                    desc_section = soup.find('div', class_=re.compile(r'description|intro|detail'))
                    if desc_section:
                        details['description'] = desc_section.get_text(strip=True)[:500]  # 限制長度
                    
                    return details
                    
        except Exception as e:
            logger.error(f"momo獲取產品詳情失敗: {e}")
            return {} 