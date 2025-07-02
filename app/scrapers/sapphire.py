#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import aiohttp
import asyncio
from bs4 import BeautifulSoup
import json
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, quote_plus
import logging

from .base_scraper import BaseScraper
from ..models.product import Product

logger = logging.getLogger(__name__)

class SapphireScraper(BaseScraper):
    """藍寶石官網爬蟲"""
    
    def __init__(self):
        super().__init__("藍寶石官網")
        self.base_url = "https://sapphiretech.cyberbiz.co"
        self.search_url = f"{self.base_url}/search"
        self.name = "SapphireScraper"
        # 設置特定的headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    async def search_products(self, query: str, max_results: int = 50, **kwargs) -> List[Product]:
        """搜尋產品"""
        try:
            logger.info(f"藍寶石官網搜尋: {query}")
            
            async with aiohttp.ClientSession() as session:
                # 首先獲取搜尋頁面
                search_page_url = f"{self.search_url}?q={quote_plus(query)}"
                logger.info(f"藍寶石搜尋URL: {search_page_url}")
                
                async with session.get(
                    search_page_url,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status != 200:
                        logger.error(f"藍寶石搜尋請求失敗，狀態碼: {response.status}")
                        return []
                    
                    html_content = await response.text()
                    logger.info(f"藍寶石獲取HTML內容，長度: {len(html_content)}")
                    
                    # 解析HTML
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # 方法1：嘗試從HTML直接解析產品
                    products = await self._extract_products_from_html(soup, session)
                    
                    # 方法2：如果HTML方法失敗，嘗試從JavaScript中提取產品數據
                    if not products:
                        products = await self._extract_products_from_js(soup, session)
                    
                    logger.info(f"藍寶石找到 {len(products)} 個產品")
                    return products[:max_results]
                    
        except Exception as e:
            logger.error(f"藍寶石搜尋過程中發生錯誤: {e}")
            return []
    
    async def _extract_products_from_html(self, soup: BeautifulSoup, session: aiohttp.ClientSession) -> List[Product]:
        """從HTML直接解析產品"""
        products = []
        
        try:
            # 檢查搜尋結果容器
            search_results = soup.find('div', id='search-result')
            if not search_results:
                logger.info("未找到搜尋結果容器")
                return []
            
            # 嘗試不同的產品容器選擇器
            selectors = [
                '.product-item',
                '.product-card', 
                '.product',
                '.search-item',
                '[data-product-id]',
                '.grid-item',
                '.item-product',
                '.product-wrapper'
            ]
            
            product_elements = []
            for selector in selectors:
                elements = search_results.select(selector)
                if elements:
                    logger.info(f"使用選擇器 {selector} 找到 {len(elements)} 個產品元素")
                    product_elements = elements
                    break
            
            # 如果沒有找到標準產品容器，嘗試查找包含產品信息的元素
            if not product_elements:
                # 查找包含價格和名稱的元素
                all_elements = search_results.find_all(['div', 'article', 'section'])
                for element in all_elements:
                    element_text = element.get_text().lower()
                    # 檢查是否包含產品相關信息
                    if any(keyword in element_text for keyword in ['nt$', 'price', '價格', 'sapphire', '藍寶石']):
                        # 檢查是否有鏈接
                        if element.find('a'):
                            product_elements.append(element)
            
            logger.info(f"總共找到 {len(product_elements)} 個潛在產品元素")
            
            for element in product_elements:
                product = await self._parse_product_element(element)
                if product:
                    products.append(product)
            
            return products
            
        except Exception as e:
            logger.error(f"從HTML解析產品時發生錯誤: {e}")
            return []
    
    async def _extract_products_from_js(self, soup: BeautifulSoup, session: aiohttp.ClientSession) -> List[Product]:
        """從JavaScript數據中提取產品"""
        products = []
        
        try:
            # 尋找包含產品數據的script標籤
            script_tags = soup.find_all('script')
            
            for script in script_tags:
                if not script.string:
                    continue
                
                script_content = script.string
                
                # 方法1：從Facebook Pixel追蹤代碼中提取產品ID和價格
                if 'fbq(' in script_content and 'content_ids' in script_content:
                    logger.info("找到Facebook Pixel追蹤代碼，嘗試提取產品數據")
                    
                    # 提取content_ids
                    content_ids_match = re.search(r'content_ids:\s*\[([^\]]+)\]', script_content)
                    if content_ids_match:
                        ids_str = content_ids_match.group(1)
                        product_ids = [id.strip() for id in ids_str.split(',')]
                        logger.info(f"找到產品IDs: {product_ids}")
                        
                        # 提取價格和數量信息
                        price_pattern = r'\{"id":(\d+),"price":([0-9.]+),"quantity":(\d+)\}'
                        price_matches = re.findall(price_pattern, script_content)
                        
                        price_dict = {}
                        for id_str, price_str, quantity_str in price_matches:
                            price_dict[id_str] = {
                                'price': float(price_str),
                                'quantity': int(quantity_str)
                            }
                        
                        logger.info(f"找到價格信息: {price_dict}")
                        
                        # 為每個產品ID創建產品對象
                        for product_id in product_ids:
                            clean_id = product_id.strip()
                            if clean_id in price_dict:
                                price_info = price_dict[clean_id]
                                
                                # 構建產品URL - 嘗試多種可能的URL格式
                                possible_urls = [
                                    f"{self.base_url}/products/{clean_id}",
                                    f"{self.base_url}/product/{clean_id}",
                                    f"{self.base_url}/collections/all/products/{clean_id}"
                                ]
                                
                                # 創建基本產品信息
                                product = Product(
                                    store="藍寶石官網",
                                    product_name=f"藍寶石產品 #{clean_id}",  # 暫時使用ID作為名稱
                                    price=price_info['price'],
                                    url=possible_urls[0],  # 使用第一個URL格式
                                    in_stock=price_info['quantity'] > 0
                                )
                                products.append(product)
                                logger.info(f"創建產品: ID={clean_id}, 價格={price_info['price']}, 庫存={price_info['quantity']}")
                
                # 方法2：從Google Analytics或其他追蹤代碼中提取產品名稱
                if any(keyword in script_content for keyword in ['9070', 'RX', 'SAPPHIRE', 'PULSE']):
                    logger.info("找到包含產品關鍵字的JavaScript")
                    
                    # 提取產品名稱模式
                    name_patterns = [
                        r'"name":"([^"]*(?:9070|RX|SAPPHIRE|PULSE)[^"]*)"',
                        r'"product_name":"([^"]*(?:9070|RX|SAPPHIRE|PULSE)[^"]*)"',
                        r'"title":"([^"]*(?:9070|RX|SAPPHIRE|PULSE)[^"]*)"'
                    ]
                    
                    # 收集所有找到的產品名稱
                    found_names = []
                    for pattern in name_patterns:
                        matches = re.findall(pattern, script_content, re.IGNORECASE)
                        for match in matches:
                            # 清理產品名稱
                            clean_name = match.replace('\\u2122', '™').replace('\\', '')
                            if clean_name not in found_names:
                                found_names.append(clean_name)
                    
                    # 嘗試將產品名稱與已有的產品(從Facebook Pixel獲取)匹配
                    for clean_name in found_names:
                        updated = False
                        for p in products:
                            if p.product_name.startswith("藍寶石產品 #"):
                                # 更新現有產品的名稱
                                p.product_name = clean_name
                                logger.info(f"更新產品名稱: {clean_name}")
                                updated = True
                                break
                        
                        # 如果沒有找到對應的產品，嘗試從產品頁面獲取更多信息
                        if not updated:
                            # 嘗試從搜尋結果頁面提取價格和URL
                            price, url = await self._try_extract_price_and_url(clean_name, session)
                            
                            product = Product(
                                store="藍寶石官網",
                                product_name=clean_name,
                                price=price if price else 0.0,
                                url=url if url else f"{self.base_url}/search?q={clean_name.split()[-1]}",  # 使用搜尋URL作為備用
                                in_stock=True if price and price > 0 else False
                            )
                            products.append(product)
                            logger.info(f"找到新產品: {clean_name} - 價格: {price} - URL: {url}")
                
                # 方法3：查找其他可能的產品數據結構
                if 'renderSearchPage' in script_content or 'search-result' in script_content:
                    logger.info("找到搜尋頁面渲染相關的JavaScript")
                    
                    # 嘗試提取產品數據
                    json_patterns = [
                        r'products\s*:\s*(\[.*?\])',
                        r'items\s*:\s*(\[.*?\])',
                        r'searchResults\s*:\s*(\[.*?\])',
                        r'data\s*:\s*(\{.*?\})'
                    ]
                    
                    for pattern in json_patterns:
                        matches = re.findall(pattern, script_content, re.DOTALL)
                        for match in matches:
                            try:
                                data = json.loads(match)
                                if isinstance(data, list):
                                    for item in data:
                                        if isinstance(item, dict):
                                            product = self._parse_json_product(item)
                                            if product:
                                                products.append(product)
                                elif isinstance(data, dict):
                                    products_data = self._extract_products_from_json(data)
                                    products.extend(products_data)
                            except:
                                continue
            
            # 過濾和優化產品列表
            filtered_products = []
            
            # 優先保留有價格的產品
            products_with_price = [p for p in products if p.price > 0]
            products_without_price = [p for p in products if p.price == 0]
            
            # 首先添加有價格的產品
            filtered_products.extend(products_with_price)
            
            # 對於沒有價格的產品，只保留看起來是具體產品的（避免太多通用類別）
            for product in products_without_price:
                name = product.product_name.lower()
                # 只保留包含具體型號的產品，排除通用系列名稱
                if any(keyword in name for keyword in ['9070', '9060', 'nitro', 'pulse', 'pure']) and \
                   not any(generic in name for generic in ['系列', 'series', '000系列']):
                    filtered_products.append(product)
            
            # 限制結果數量，避免太多無價格產品
            if len(filtered_products) > 10:
                # 優先保留有價格的產品，然後是具體型號的產品
                filtered_products = products_with_price + products_without_price[:10-len(products_with_price)]
            
            logger.info(f"從JavaScript提取到 {len(products)} 個產品，過濾後保留 {len(filtered_products)} 個")
            logger.info(f"其中有價格的產品: {len(products_with_price)} 個")
            
            return filtered_products
            
        except Exception as e:
            logger.error(f"從JavaScript提取產品時發生錯誤: {e}")
            return []
    
    def _extract_products_from_json(self, data: Dict[str, Any]) -> List[Product]:
        """從JSON數據中提取產品"""
        products = []
        
        try:
            # 嘗試不同的JSON結構
            product_lists = []
            
            # 直接檢查是否為產品列表
            if isinstance(data, list):
                product_lists.append(data)
            elif isinstance(data, dict):
                # 檢查常見的產品數據鍵
                for key in ['products', 'items', 'results', 'data', 'product_list']:
                    if key in data and isinstance(data[key], list):
                        product_lists.append(data[key])
                
                # 遞歸檢查嵌套結構
                for value in data.values():
                    if isinstance(value, dict):
                        nested_products = self._extract_products_from_json(value)
                        if nested_products:
                            products.extend(nested_products)
            
            # 解析每個產品列表
            for product_list in product_lists:
                for item in product_list:
                    if isinstance(item, dict):
                        product = self._parse_json_product(item)
                        if product:
                            products.append(product)
            
            return products
            
        except Exception as e:
            logger.error(f"從JSON提取產品時發生錯誤: {e}")
            return []
    
    def _parse_json_product(self, item: Dict[str, Any]) -> Optional[Product]:
        """解析JSON格式的產品數據"""
        try:
            # 提取產品名稱
            name = self._get_json_value(item, ['name', 'title', 'product_name', 'product_title'])
            if not name:
                return None
            
            # 提取價格
            price = self._get_json_value(item, ['price', 'current_price', 'selling_price', 'amount'])
            if price:
                price = self._parse_price(str(price))
            
            # 提取產品ID
            product_id = self._get_json_value(item, ['id', 'product_id', 'sku', 'handle'])
            
            # 提取產品URL
            url = self._get_json_value(item, ['url', 'link', 'href', 'product_url'])
            if url and not url.startswith('http'):
                url = urljoin(self.base_url, url)
            
            # 提取庫存狀態
            stock_status = self._get_stock_status_from_json(item)
            
            # 提取圖片URL
            image_url = self._get_json_value(item, ['image', 'image_url', 'thumbnail', 'photo'])
            if image_url and not image_url.startswith('http'):
                image_url = urljoin(self.base_url, image_url)
            
            return Product(
                store="藍寶石官網",
                product_name=name,
                price=price or 0.0,
                url=url or "",
                in_stock=stock_status == "有庫存",
                image_url=image_url
            )
            
        except Exception as e:
            logger.error(f"解析JSON產品時發生錯誤: {e}")
            return None
    
    def _get_json_value(self, data: Dict[str, Any], keys: List[str]) -> Any:
        """從JSON數據中獲取值，嘗試多個可能的鍵"""
        for key in keys:
            if key in data and data[key]:
                return data[key]
        return None
    
    def _get_stock_status_from_json(self, item: Dict[str, Any]) -> str:
        """從JSON數據中獲取庫存狀態"""
        # 檢查庫存相關字段
        stock_fields = ['stock', 'inventory', 'available', 'in_stock', 'stock_status']
        
        for field in stock_fields:
            if field in item:
                value = item[field]
                if isinstance(value, bool):
                    return "有庫存" if value else "無庫存"
                elif isinstance(value, (int, float)):
                    return "有庫存" if value > 0 else "無庫存"
                elif isinstance(value, str):
                    return self._parse_stock_status(value)
        
        # 檢查價格是否存在作為庫存指標
        price = self._get_json_value(item, ['price', 'current_price', 'selling_price'])
        if price and price > 0:
            return "有庫存"
        
        return "需確認庫存"
    
    async def _try_extract_price_and_url(self, product_name: str, session: aiohttp.ClientSession) -> tuple:
        """嘗試從產品名稱提取價格和URL"""
        try:
            # 從產品名稱中提取可能的型號
            model_patterns = [
                r'RX\s*(\d+)',  # RX 9070
                r'PULSE.*?(RX.*?)(?:\s|$)',  # PULSE RX 9070
                r'NITRO.*?(RX.*?)(?:\s|$)',  # NITRO+ RX 9070
                r'PURE.*?(RX.*?)(?:\s|$)'   # PURE RX 9070
            ]
            
            model = None
            for pattern in model_patterns:
                match = re.search(pattern, product_name, re.IGNORECASE)
                if match:
                    model = match.group(1)
                    break
            
            if not model:
                return None, None
            
            # 嘗試從當前頁面的HTML中查找對應的產品信息
            # 由於這是JavaScript渲染的網站，我們嘗試從已加載的內容中查找
            
            # 構建可能的產品URL
            possible_urls = [
                f"{self.base_url}/products/{model.lower().replace(' ', '-')}",
                f"{self.base_url}/products/rx-{model.split()[-1] if ' ' in model else model}",
                f"{self.base_url}/search?q={model}"
            ]
            
            # 返回搜尋URL作為備用
            search_url = f"{self.base_url}/search?q={model}"
            
            # 暫時返回None價格和搜尋URL
            # 在未來的版本中可以嘗試訪問這些URL來獲取實際價格
            return None, search_url
            
        except Exception as e:
            logger.error(f"提取價格和URL時發生錯誤: {e}")
            return None, None
    
    async def _parse_product_element(self, element) -> Optional[Product]:
        """解析HTML產品元素"""
        try:
            # 提取產品名稱
            name_selectors = [
                '.product-title', '.product-name', '.title', 
                'h1', 'h2', 'h3', '.name', '[data-product-title]',
                'a[title]'  # 鏈接的title屬性
            ]
            name = self._extract_text_by_selectors(element, name_selectors)
            
            # 如果沒有找到名稱，嘗試從鏈接的title屬性獲取
            if not name:
                link_element = element.find('a')
                if link_element and link_element.get('title'):
                    name = link_element['title'].strip()
            
            if not name:
                return None
            
            # 提取價格
            price_selectors = [
                '.price', '.product-price', '.current-price',
                '.selling-price', '[data-price]', '.amount',
                '.money', '.cost'
            ]
            price_text = self._extract_text_by_selectors(element, price_selectors)
            price = self._parse_price(price_text) if price_text else None
            
            # 提取產品URL
            url = None
            link_element = element.find('a')
            if link_element and link_element.get('href'):
                href = link_element['href']
                if href.startswith('/'):
                    url = urljoin(self.base_url, href)
                elif href.startswith('http'):
                    url = href
            
            # 提取庫存狀態
            stock_status = self._get_stock_status_from_element(element)
            
            # 提取圖片URL
            image_url = None
            img_element = element.find('img')
            if img_element:
                src = img_element.get('src') or img_element.get('data-src')
                if src:
                    if src.startswith('/'):
                        image_url = urljoin(self.base_url, src)
                    elif src.startswith('http'):
                        image_url = src
            
            return Product(
                store="藍寶石官網",
                product_name=name,
                price=price or 0.0,
                url=url or "",
                in_stock=stock_status == "有庫存",
                image_url=image_url
            )
            
        except Exception as e:
            logger.error(f"解析產品元素時發生錯誤: {e}")
            return None
    
    def _extract_text_by_selectors(self, element, selectors: List[str]) -> Optional[str]:
        """使用多個選擇器嘗試提取文本"""
        for selector in selectors:
            target = element.select_one(selector)
            if target:
                text = target.get_text(strip=True)
                if text:
                    return text
        return None
    
    def _get_stock_status_from_element(self, element) -> str:
        """從HTML元素中獲取庫存狀態"""
        # 檢查庫存相關的文本
        element_text = element.get_text().lower()
        
        # 缺貨指標
        out_of_stock_indicators = [
            '缺貨', '售完', '暫停供應', '停產', '預購', '補貨中',
            'out of stock', 'sold out', 'unavailable', 'coming soon'
        ]
        
        for indicator in out_of_stock_indicators:
            if indicator in element_text:
                return "無庫存"
        
        # 有庫存指標
        in_stock_indicators = [
            '現貨', '有庫存', '立即購買', '加入購物車', '購買',
            'in stock', 'available', 'add to cart', 'buy now'
        ]
        
        for indicator in in_stock_indicators:
            if indicator in element_text:
                return "有庫存"
        
        # 檢查是否有價格作為庫存指標
        price_selectors = ['.price', '.product-price', '.amount', '.money']
        for selector in price_selectors:
            price_element = element.select_one(selector)
            if price_element:
                price_text = price_element.get_text(strip=True)
                if price_text and any(char.isdigit() for char in price_text):
                    return "有庫存"
        
        return "需確認庫存"
    
    def _parse_price(self, price_text: str) -> Optional[float]:
        """解析價格文本"""
        if not price_text:
            return None
        
        try:
            # 移除常見的價格前綴和符號
            price_text = re.sub(r'[NT$\$,，\s]', '', price_text)
            
            # 提取數字
            price_match = re.search(r'(\d+(?:\.\d+)?)', price_text)
            if price_match:
                return float(price_match.group(1))
                
        except Exception as e:
            logger.error(f"解析價格時發生錯誤: {e}")
        
        return None
    
    def _parse_stock_status(self, status_text: str) -> str:
        """解析庫存狀態文本"""
        if not status_text:
            return "需確認庫存"
        
        status_text = status_text.lower()
        
        if any(keyword in status_text for keyword in ['out', 'sold', 'unavailable', '缺貨', '售完']):
            return "無庫存"
        elif any(keyword in status_text for keyword in ['in stock', 'available', '有庫存', '現貨']):
            return "有庫存"
        else:
            return "需確認庫存"

    async def get_product_details(self, product_url: str) -> Dict[str, Any]:
        """獲取產品詳細資訊"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    product_url,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status != 200:
                        return {}
                    
                    html_content = await response.text()
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # 提取詳細資訊
                    details = {}
                    
                    # 產品描述
                    desc_selectors = [
                        '.product-description', '.description', 
                        '.product-details', '[data-description]'
                    ]
                    description = self._extract_text_by_selectors(soup, desc_selectors)
                    if description:
                        details['description'] = description
                    
                    # 規格資訊
                    spec_selectors = [
                        '.specifications', '.specs', '.product-specs',
                        '.technical-details', '[data-specs]'
                    ]
                    specs = self._extract_text_by_selectors(soup, spec_selectors)
                    if specs:
                        details['specifications'] = specs
                    
                    return details
                    
        except Exception as e:
            logger.error(f"獲取產品詳情時發生錯誤: {e}")
            return {}
    
    def _build_search_url(self, product_name: str) -> str:
        """建立搜尋URL - 實現抽象方法"""
        return f"{self.search_url}?q={quote_plus(product_name)}"
    
    def _parse_product_list(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """解析產品列表 - 實現抽象方法"""
        # 這個方法由於藍寶石網站的特殊性，我們主要使用其他方法解析
        # 但為了滿足抽象方法要求，提供一個基本實現
        products = []
        
        # 檢查搜尋結果容器
        search_results = soup.find('div', id='search-result')
        if not search_results:
            return products
        
        # 嘗試找到產品元素
        product_elements = search_results.find_all(['div', 'article'], class_=re.compile(r'product|item'))
        
        for element in product_elements:
            try:
                # 提取基本信息
                name_elem = element.find(['h1', 'h2', 'h3', 'a'])
                if name_elem:
                    name = name_elem.get_text(strip=True)
                    if name:
                        product_data = {
                            'name': name,
                            'price': None,
                            'url': None,
                            'stock_status': '需確認庫存'
                        }
                        
                        # 嘗試提取價格
                        price_elem = element.find(class_=re.compile(r'price|cost|amount'))
                        if price_elem:
                            price_text = price_elem.get_text(strip=True)
                            product_data['price'] = self._parse_price(price_text)
                        
                        # 嘗試提取URL
                        link_elem = element.find('a')
                        if link_elem and link_elem.get('href'):
                            product_data['url'] = urljoin(self.base_url, link_elem['href'])
                        
                        products.append(product_data)
            except Exception as e:
                logger.error(f"解析產品元素時發生錯誤: {e}")
                continue
        
        return products 