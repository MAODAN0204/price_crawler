#!/usr/bin/env python3
"""順發電腦爬蟲模組"""

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

class SunfarScraper(BaseScraper):
    """順發電腦爬蟲"""
    
    def __init__(self):
        super().__init__("順發電腦")
        self.base_url = "https://www.isunfar.com.tw"
        self.search_url = f"{self.base_url}/product/search.aspx"
    
    async def search_products(self, query: str, max_results: int = 50, **kwargs) -> List[Product]:
        """搜尋產品"""
        try:
            logger.info(f"順發電腦搜尋: {query}")
            
            # 構建搜尋URL
            search_url = f"{self.search_url}?b=undefined&keyword={quote(query)}"
            logger.info(f"順發電腦搜尋URL: {search_url}")
            
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers=self.get_headers()
            ) as session:
                async with session.get(search_url) as response:
                    if response.status != 200:
                        logger.error(f"順發電腦請求失敗: {response.status}")
                        return []
                    
                    html = await response.text()
                    logger.info(f"順發電腦頁面長度: {len(html)} 字符")
                    
                                # 從JavaScript中提取產品數據
            products = await self._extract_products_from_js(html, session)
            
            # 去除重複產品（基於產品ID）
            unique_products = []
            seen_ids = set()
            
            for product in products:
                # 從URL中提取產品ID
                product_id = None
                if product.url and 'id=' in product.url:
                    try:
                        product_id = product.url.split('id=')[1].split('&')[0]
                    except:
                        product_id = product.url
                
                # 如果沒有ID，使用產品名稱和價格作為唯一標識
                if not product_id:
                    product_id = f"{product.product_name}_{product.price}"
                
                if product_id not in seen_ids:
                    seen_ids.add(product_id)
                    unique_products.append(product)
            
            logger.info(f"順發電腦成功解析 {len(unique_products)} 個獨特產品（原始: {len(products)}）")
            return unique_products[:max_results]
                    
        except Exception as e:
            logger.error(f"順發電腦搜尋失敗: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def _extract_products_from_js(self, html: str, session: aiohttp.ClientSession) -> List[Product]:
        """從JavaScript中提取產品數據"""
        products = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找包含Search_data的script標籤
            scripts = soup.find_all('script')
            
            for script in scripts:
                if not script.string:
                    continue
                
                content = script.string
                
                # 查找Search_data變量
                if 'Search_data' in content:
                    logger.info("找到Search_data變量")
                    
                    # 提取Search_data的JSON內容
                    match = re.search(r'var Search_data\s*=\s*({.*?});', content, re.DOTALL)
                    if match:
                        try:
                            json_str = match.group(1)
                            data = json.loads(json_str)
                            
                            # 從ptlist中提取產品
                            if 'ptlist' in data and isinstance(data['ptlist'], list):
                                logger.info(f"找到 {len(data['ptlist'])} 個產品")
                                
                                for item in data['ptlist']:
                                    product = self._parse_product_item(item)
                                    if product:
                                        products.append(product)
                            
                            break
                            
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON解析失敗: {e}")
                            continue
            
            return products
            
        except Exception as e:
            logger.error(f"從JavaScript提取產品時發生錯誤: {e}")
            return []
    
    def _parse_product_item(self, item: Dict[str, Any]) -> Optional[Product]:
        """解析單個產品項目"""
        try:
            # 提取產品名稱
            product_name = item.get('pname', '').strip()
            if not product_name:
                return None
            
            # 提取價格
            price = 0.0
            price_fields = ['prod_price', 'mem_price1', 'search_price2_da']
            for field in price_fields:
                if field in item and item[field]:
                    try:
                        price = float(item[field])
                        break
                    except (ValueError, TypeError):
                        continue
            
            # 提取產品ID
            product_id = item.get('id', '')
            
            # 構建產品URL
            product_url = ""
            if product_id:
                product_url = f"{self.base_url}/product/proddetail.aspx?id={product_id}"
            
            # 提取庫存狀態
            in_stock = self._get_stock_status(item)
            
            # 提取圖片URL
            image_url = None
            if 'ps' in item and item['ps']:
                image_url = f"{self.base_url}/upload/product/{item['ps']}"
            
            # 提取規格信息
            specifications = ""
            if 'bd' in item and item['bd']:
                specifications = item['bd'].strip()
            
            product = Product(
                store="順發電腦",
                product_name=product_name,
                price=price,
                url=product_url,
                in_stock=in_stock,
                image_url=image_url,
                specifications=specifications
            )
            
            logger.debug(f"解析產品: {product_name} - NT${price} - {'有庫存' if in_stock else '無庫存'}")
            return product
            
        except Exception as e:
            logger.error(f"解析產品項目時發生錯誤: {e}")
            return None
    
    def _get_stock_status(self, item: Dict[str, Any]) -> bool:
        """獲取庫存狀態"""
        try:
            # 檢查庫存數量
            if 'pos_qty' in item:
                try:
                    qty = int(item['pos_qty'])
                    return qty > 0
                except (ValueError, TypeError):
                    pass
            
            # 檢查是否可購買
            if 'buy' in item:
                buy_status = str(item['buy']).lower()
                if buy_status in ['1', 'true', 'y', 'yes']:
                    return True
                elif buy_status in ['0', 'false', 'n', 'no']:
                    return False
            
            # 檢查產品狀態
            if 'prodseqstate_no' in item:
                state = str(item['prodseqstate_no'])
                # 通常狀態1表示正常販售
                return state == '1'
            
            # 檢查是否有價格作為庫存指標
            price_fields = ['prod_price', 'mem_price1', 'search_price2_da']
            for field in price_fields:
                if field in item and item[field]:
                    try:
                        price = float(item[field])
                        if price > 0:
                            return True
                    except (ValueError, TypeError):
                        continue
            
            # 預設返回有庫存（順發通常不會顯示缺貨商品）
            return True
            
        except Exception as e:
            logger.error(f"檢查庫存狀態時發生錯誤: {e}")
            return True
    
    def get_headers(self) -> Dict[str, str]:
        """獲取請求標頭"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.isunfar.com.tw/'
        }
    
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
                    spec_table = soup.find('table', class_='spec-table')
                    if spec_table:
                        specs = []
                        for row in spec_table.find_all('tr'):
                            cells = row.find_all(['td', 'th'])
                            if len(cells) >= 2:
                                key = cells[0].get_text(strip=True)
                                value = cells[1].get_text(strip=True)
                                if key and value:
                                    specs.append(f"{key}: {value}")
                        details['specifications'] = '; '.join(specs)
                    
                    # 提取更多圖片
                    images = []
                    img_elements = soup.find_all('img', src=True)
                    for img in img_elements:
                        src = img.get('src')
                        if src and 'product' in src.lower():
                            full_url = urljoin(self.base_url, src)
                            images.append(full_url)
                    details['images'] = images[:5]  # 最多5張圖片
                    
                    return details
                    
        except Exception as e:
            logger.error(f"獲取產品詳細資訊失敗: {e}")
            return {}
    
    def _build_search_url(self, product_name: str) -> str:
        """構建搜尋URL"""
        return f"{self.search_url}?b=undefined&keyword={quote(product_name)}"
    
    def _parse_product_list(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """解析產品列表 - 從JavaScript中提取"""
        products = []
        
        try:
            # 查找包含Search_data的script標籤
            scripts = soup.find_all('script')
            
            for script in scripts:
                if not script.string:
                    continue
                
                content = script.string
                
                # 查找Search_data變量
                if 'Search_data' in content:
                    # 提取Search_data的JSON內容
                    match = re.search(r'var Search_data\s*=\s*({.*?});', content, re.DOTALL)
                    if match:
                        try:
                            json_str = match.group(1)
                            data = json.loads(json_str)
                            
                            # 從ptlist中提取產品
                            if 'ptlist' in data and isinstance(data['ptlist'], list):
                                for item in data['ptlist']:
                                    # 轉換為字典格式
                                    product_dict = {
                                        'name': item.get('pname', ''),
                                        'price': item.get('prod_price', 0),
                                        'url': f"{self.base_url}/product/proddetail.aspx?id={item.get('id', '')}" if item.get('id') else '',
                                        'in_stock': self._get_stock_status(item),
                                        'image': f"{self.base_url}/upload/product/{item['ps']}" if item.get('ps') else None,
                                        'specifications': item.get('bd', '')
                                    }
                                    products.append(product_dict)
                            
                            break
                            
                        except json.JSONDecodeError:
                            continue
            
            return products
            
        except Exception as e:
            logger.error(f"解析產品列表時發生錯誤: {e}")
            return [] 