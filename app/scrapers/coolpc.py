#!/usr/bin/env python3
"""
原價屋 (CoolPC) 爬蟲
"""

import logging
import re
import asyncio
import json
from urllib.parse import urljoin, quote, parse_qs, urlparse
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from ..models.product import Product

logger = logging.getLogger(__name__)

class CoolPCScraper(BaseScraper):
    """原價屋爬蟲"""
    
    def __init__(self):
        super().__init__("原價屋")
        self.base_url = "https://www.coolpc.com.tw"
        self.evaluate_url = f"{self.base_url}/evaluate.php"
    
    def get_headers(self) -> Dict[str, str]:
        """獲取請求標頭"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def _build_search_url(self, query: str) -> str:
        """建構搜尋URL"""
        return self.evaluate_url
    
    def _parse_js_arrays(self, html: str) -> Dict[str, List]:
        """解析JavaScript中的價格數組"""
        arrays = {}
        
        # 找到所有的c1, c2, g1, g2等數組
        patterns = [
            r'c(\d+)=\[([\d,]+)\]',  # 價格數組
            r'g(\d+)=\[([\d\.,]+)\]',  # 產品規格ID數組
            r'Header=\[([\d\[\],]+)\]',  # 頭部信息
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html)
            for match in matches:
                if len(match) == 2:
                    array_name = f"c{match[0]}" if pattern.startswith('c') else f"g{match[0]}" if pattern.startswith('g') else "Header"
                    array_data = match[1].split(',')
                    arrays[array_name] = [float(x) if x and x != '0' else 0 for x in array_data]
        
        return arrays
    
    def _extract_product_names(self, html: str) -> Dict[str, str]:
        """從HTML中提取產品名稱映射"""
        products = {}
        
        # 直接使用正則表達式解析原始HTML中的OPTION標籤
        # 匹配 <OPTION value=數字>產品內容</OPTION>
        option_pattern = r'<OPTION[^>]*value=(\d+)[^>]*>([^<]+)</OPTION>'
        matches = re.findall(option_pattern, html, re.IGNORECASE | re.DOTALL)
        
        for value, text in matches:
            text = text.strip()
            # 過濾掉無效的選項，必須包含價格信息
            if text and '$' in text and len(text) > 10:
                # 清理多餘空格
                cleaned_text = re.sub(r'\s+', ' ', text)
                products[value] = cleaned_text
                
        logger.info(f"原價屋提取到 {len(products)} 個有效產品選項")
        return products
    
    def _search_products_in_data(self, query: str, arrays: Dict[str, List], product_names: Dict[str, str]) -> List[Dict[str, Any]]:
        """在解析的數據中搜尋產品"""
        results = []
        query_lower = query.lower()
        
        # 搜尋產品名稱
        for value, product_text in product_names.items():
            if query_lower in product_text.lower():
                try:
                    # 解析產品名稱和價格
                    # 格式：產品名稱, $價格
                    if '$' in product_text:
                        parts = product_text.split('$')
                        if len(parts) >= 2:
                            product_name = parts[0].strip().rstrip(',').strip()
                            price_part = parts[1].split()[0]  # 取第一個部分，去掉後面的空格和其他文字
                            
                            # 清理價格字符串
                            price_str = re.sub(r'[^\d]', '', price_part)
                            if price_str:
                                price = float(price_str)
                                
                                if price > 0 and product_name:
                                    product_data = {
                                        'store': '原價屋',
                                        'product_name': product_name,
                                        'price': price,
                                        'url': f"{self.base_url}/evaluate.php",
                                        'in_stock': True,
                                        'image_url': None,
                                        'option_value': value
                                    }
                                    results.append(product_data)
                
                except (ValueError, IndexError) as e:
                    logger.debug(f"解析產品失敗 {value}: {e}")
                    continue
        
        return results
    
    def _parse_product_list(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """解析產品列表 - 實現基類的抽象方法"""
        # 這個方法不會被直接調用，因為我們重寫了search_products
        return []
    
    async def search_products(self, query: str, max_results: int = 20, standalone_only: bool = False) -> List[Product]:
        """搜尋產品"""
        try:
            search_url = self._build_search_url(query)
            logger.info(f"原價屋搜尋URL: {search_url}")
            
            # 獲取主頁面
            html = await self._fetch_page(search_url)
            if not html:
                logger.warning("原價屋無法獲取頁面內容")
                return []
            
            logger.info(f"原價屋頁面長度: {len(html)} 字符")
            
            # 直接從原始HTML搜尋產品
            products = self._search_products_direct(query, html, max_results)
            
            # 如果只要單獨商品，過濾掉專案商品
            if standalone_only:
                products = [p for p in products if not p.is_bundle]
                logger.info(f"原價屋過濾後剩餘 {len(products)} 個單獨商品")
            
            logger.info(f"原價屋搜尋到 {len(products)} 個相關產品")
            
            return products
            
        except Exception as e:
            logger.error(f"原價屋搜尋產品時發生錯誤: {e}")
            return []
    
    def _is_bundle_product(self, product_name: str) -> bool:
        """檢測是否為專案商品或需搭配商品"""
        bundle_keywords = [
            '專案', '需搭配', 'CPU合購', '[需搭配', '[專案',
            '搭配主板', '搭配CPU', '限定搭配', '合購優惠',
            'f主板', 'fCPU', 'f搭配'
        ]
        
        product_lower = product_name.lower()
        for keyword in bundle_keywords:
            if keyword.lower() in product_lower:
                return True
        
        return False
    
    def _clean_product_name(self, text: str) -> str:
        """清理產品名稱中的特殊字符和編碼問題"""
        
        # 先移除明顯的亂碼字符，只保留可讀字符
        # 保留英文、數字、中文、常見符號
        cleaned_text = re.sub(r'[^\w\s\-\(\)\[\]/\+\.\u4e00-\u9fff]+', ' ', text)
        
        # 清理多餘空格
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        
        # 基本的字詞替換，修復一些可能的解析問題
        simple_fixes = {
            '_': '藍寶石',
            'fB760': '[需搭配B760]',
            'fB850': '[需搭配B850]', 
            'fB860': '[需搭配B860]',
            'fZ790': '[需搭配Z790]',
            'fZ890': '[需搭配Z890]',
            'fX370': '[需搭配X370]',
            'fX3D': '[需搭配X3D]',
            'CDO': '主板',
            'dM': '專案',
            'AM': '專案',
            'GRE': 'GRE',
            'XT': 'XT',
            'ݷf': '[需搭配]',
            'ݥf': '[需搭配]',
            'Xʡ': 'CPU合購',
            'ݭI': '金屬背板',
            'U O': '三年保固',
            'T O': '三年保固',
            'T OT': '三年保固',
            'ʤ': '限購一片',
            'MITxWs': 'MIT台灣製',
            'a ': '極地 ',
            't ': '暗黑 '
        }
        
        for old, new in simple_fixes.items():
            cleaned_text = cleaned_text.replace(old, new)
        
        # 清理重複的括號和專案標記
        cleaned_text = re.sub(r'\[\s*專案\s*\]', '[專案]', cleaned_text)
        cleaned_text = re.sub(r'\[\s*A\s*-專案\s*\]', '[專案]', cleaned_text)
        
        return cleaned_text.strip()
    
    def _search_products_direct(self, query: str, html: str, max_results: int) -> List[Product]:
        """直接從原始HTML搜尋產品"""
        products = []
        query_lower = query.lower()
        
        # 直接搜尋包含查詢詞的OPTION標籤
        option_pattern = r'<OPTION[^>]*value=(\d+)[^>]*>([^<]*' + re.escape(query) + r'[^<]*)</OPTION>'
        matches = re.findall(option_pattern, html, re.IGNORECASE | re.DOTALL)
        
        for value, text in matches:
            text = text.strip()
            
            # 必須包含價格信息
            if '$' in text:
                try:
                    # 解析價格
                    price_match = re.search(r'\$(\d+)', text)
                    if price_match:
                        price = float(price_match.group(1))
                        
                        # 提取產品名稱（去掉價格部分）
                        product_name = re.sub(r',?\s*\$\d+.*$', '', text).strip()
                        
                        # 清理產品名稱中的編碼問題
                        clean_name = self._clean_product_name(product_name)
                        
                        if price > 0 and clean_name:
                            # 檢測是否為專案或需搭配商品
                            is_bundle = self._is_bundle_product(clean_name)
                            
                            product = Product(
                                store='原價屋',
                                product_name=clean_name,
                                price=price,
                                url=f"{self.base_url}/evaluate.php",
                                in_stock=True,
                                currency="TWD",
                                image_url=None,
                                specifications=None,
                                is_bundle=is_bundle
                            )
                            products.append(product)
                            
                            if len(products) >= max_results:
                                break
                                
                except (ValueError, AttributeError) as e:
                    logger.debug(f"原價屋解析產品失敗 {value}: {e}")
                    continue
        
        return products 