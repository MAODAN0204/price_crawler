#!/usr/bin/env python3
"""三井3C購物網爬蟲模組"""

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

class SanjingScraper(BaseScraper):
    """三井3C購物網爬蟲"""
    
    def __init__(self):
        super().__init__("三井3C")
        self.base_url = "https://www.sanjing3c.com.tw"
        self.search_url = "https://www.sanjing3c.com.tw/search.php"
    
    def _build_search_url(self, query: str) -> str:
        """建構搜尋URL"""
        encoded_query = quote(query)
        return f"{self.search_url}?k={encoded_query}"
    
    def _parse_product_list(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """解析產品列表 - 實現基類的抽象方法"""
        products = []
        
        try:
            # 查找產品容器
            search_result_container = soup.find('div', class_='search-result')
            if not search_result_container:
                logger.warning("未找到搜尋結果容器")
                return []
            
            # 查找所有產品項目
            product_items = search_result_container.find_all('div', class_='prod-box')
            logger.info(f"找到 {len(product_items)} 個產品")
            
            for item in product_items:
                try:
                    product_data = self._parse_product_item_data(item)
                    if product_data:
                        products.append(product_data)
                except Exception as e:
                    logger.error(f"解析產品時發生錯誤: {e}")
                    continue
            
            return products
            
        except Exception as e:
            logger.error(f"解析產品列表時發生錯誤: {e}")
            return []
    
    def _parse_product_item_data(self, item) -> Dict[str, Any]:
        """解析單個產品項目為字典格式（配合基類）"""
        try:
            # 獲取產品連結
            link_elem = item.find_parent('a')
            if not link_elem:
                return None
            
            product_url = link_elem.get('href', '')
            if product_url and not product_url.startswith('http'):
                product_url = urljoin(self.base_url, product_url)
            
            # 獲取產品名稱
            name_elem = item.find('div', class_='name')
            product_name = name_elem.get_text(strip=True) if name_elem else "未知產品"
            
            # 獲取價格
            price_elem = item.find('div', class_='price')
            price = 0.0
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_match = re.search(r'[\d,]+', price_text.replace('$', '').replace(',', ''))
                if price_match:
                    try:
                        price = float(price_match.group().replace(',', ''))
                    except ValueError:
                        price = 0.0
            
            # 獲取圖片URL
            img_elem = item.find('img')
            image_url = None
            if img_elem:
                src = img_elem.get('src', '')
                if src and not src.startswith('http'):
                    image_url = urljoin(self.base_url, src)
                else:
                    image_url = src
            
            return {
                "store": "三井3C",
                "product_name": product_name,
                "price": price,
                "url": product_url,
                "in_stock": True,  # 三井3C默認有庫存
                "image_url": image_url
            }
            
        except Exception as e:
            logger.error(f"解析產品項目數據時發生錯誤: {e}")
            return None
    
    async def search_products(self, query: str, max_results: int = 20) -> List[Product]:
        """搜尋產品"""
        try:
            search_url = self._build_search_url(query)
            logger.info(f"搜尋URL: {search_url}")
            
            html = await self._fetch_page(search_url)
            if not html:
                logger.error("無法獲取頁面內容")
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找產品容器 - 更新為正確的選擇器
            search_result_container = soup.find('div', class_='search-result')
            if not search_result_container:
                logger.warning("未找到搜尋結果容器")
                return []
            
            # 查找所有產品項目
            product_items = search_result_container.find_all('div', class_='prod-box')
            logger.info(f"找到 {len(product_items)} 個產品")
            
            products = []
            for item in product_items[:max_results]:
                try:
                    product = self._parse_product_item(item)
                    if product:
                        products.append(product)
                except Exception as e:
                    logger.error(f"解析產品時發生錯誤: {e}")
                    continue
            
            logger.info(f"成功解析 {len(products)} 個產品")
            return products
            
        except Exception as e:
            logger.error(f"搜尋產品時發生錯誤: {e}")
            return []
    
    def _parse_product_item(self, item) -> Product:
        """解析單個產品項目"""
        try:
            # 獲取產品連結 - 查找父層的 a 標籤
            link_elem = item.find_parent('a')
            if not link_elem:
                logger.warning("未找到產品連結")
                return None
            
            product_url = link_elem.get('href', '')
            if product_url and not product_url.startswith('http'):
                product_url = urljoin(self.base_url, product_url)
            
            # 獲取產品名稱
            name_elem = item.find('div', class_='name')
            name = name_elem.get_text(strip=True) if name_elem else "未知產品"
            
            # 獲取價格
            price_elem = item.find('div', class_='price')
            price = 0
            price_text = ""
            
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                # 提取數字價格
                price_match = re.search(r'[\d,]+', price_text.replace('$', '').replace(',', ''))
                if price_match:
                    try:
                        price = int(price_match.group().replace(',', ''))
                    except ValueError:
                        price = 0
            
            # 獲取圖片URL
            img_elem = item.find('img')
            image_url = ""
            if img_elem:
                src = img_elem.get('src', '')
                if src and not src.startswith('http'):
                    image_url = urljoin(self.base_url, src)
                else:
                    image_url = src
            
            # 獲取描述信息
            spec_elem = item.find('div', class_='spec')
            description = ""
            if spec_elem:
                # 提取所有li標籤的內容
                li_elements = spec_elem.find_all('li')
                description_parts = [li.get_text(strip=True) for li in li_elements if li.get_text(strip=True)]
                description = " | ".join(description_parts[:3])  # 只取前3個特色
            
            if not description:
                # 如果沒有spec，嘗試獲取full-name
                full_name_elem = item.find('div', class_='full-name')
                if full_name_elem:
                    description = full_name_elem.get_text(strip=True)
            
            product = Product(
                name=name,
                price=price,
                price_text=price_text,
                url=product_url,
                image_url=image_url,
                description=description,
                store="三井3C",
                availability="有庫存"  # 三井3C默認有庫存
            )
            
            logger.debug(f"解析產品: {name} - {price_text}")
            return product
            
        except Exception as e:
            logger.error(f"解析產品項目時發生錯誤: {e}")
            return None
    
    def _check_stock_status(self, container: BeautifulSoup) -> bool:
        """檢查庫存狀態"""
        try:
            # 檢查缺貨指標
            stock_indicators = container.find_all(text=re.compile(
                r'缺貨|售完|補貨中|暫停供應|停產|預購|客定|無庫存|out.*stock|sold.*out',
                re.IGNORECASE
            ))
            
            if stock_indicators:
                return False
            
            # 檢查購買按鈕
            buy_button = container.find(['button', 'a'], class_=re.compile(r'buy|cart|purchase'))
            if buy_button:
                button_text = buy_button.get_text(strip=True)
                if re.search(r'缺貨|補貨|售完', button_text):
                    return False
            
            # 預設為有庫存
            return True
            
        except Exception as e:
            logger.error(f"三井3C檢查庫存狀態時發生錯誤: {e}")
            return True
    
    def _clean_product_name(self, name: str) -> str:
        """清理產品名稱"""
        # 移除多餘的空白
        name = re.sub(r'\s+', ' ', name.strip())
        
        # 移除特殊標記
        name = re.sub(r'【.*?】', '', name)  # 移除【】標記
        name = re.sub(r'\[.*?\]', '', name)  # 移除[]標記
        
        return name.strip()
    
 