import asyncio
import aiohttp
import urllib.parse
import re
import json
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from app.scrapers.base_scraper import BaseScraper
from app.models.product import Product

class AutobuyScraper(BaseScraper):
    """AUTOBUY購物中心爬蟲"""
    
    def __init__(self):
        super().__init__("AUTOBUY購物中心")
        self.base_url = "https://www.autobuy.tw"
        self.search_url = f"{self.base_url}/search"
    
    def _build_search_url(self, product_name: str) -> str:
        """建立搜尋URL"""
        # 根據分析，AUTOBUY使用keyword參數進行搜尋
        params = {
            'keyword': product_name
        }
        
        query_string = urllib.parse.urlencode(params, encoding='utf-8')
        return f"{self.search_url}?{query_string}"
    
    def _parse_product_list(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """解析AUTOBUY產品列表"""
        products = []
        
        print("AutoBuy: 開始解析產品列表...")
        
        # 根據分析，AUTOBUY的產品信息在 h3 > a 結構中
        product_links = soup.find_all('a', href=True)
        
        print(f"AutoBuy: 找到 {len(product_links)} 個連結")
        
        for link in product_links:
            try:
                # 查找包含產品名稱的h3標籤
                h3_elem = link.find('h3')
                if not h3_elem:
                    continue
                
                product_name = h3_elem.get_text(strip=True)
                if not product_name or len(product_name) < 10:  # 過濾太短的標題
                    continue
                
                # 檢查是否為產品頁面連結
                href = link.get('href', '')
                if not href.startswith('/') and not href.startswith('http'):
                    continue
                
                # 建立完整URL
                if href.startswith('/'):
                    product_url = f"{self.base_url}{href}"
                else:
                    product_url = href
                
                # 查找價格信息 - 在連結的父容器中查找
                price = 0
                price_container = link.parent
                
                # 向上查找更大的容器來尋找價格
                for _ in range(3):  # 最多向上查找3層
                    if price_container:
                        price_text = price_container.get_text()
                        found_price = self._extract_price_from_text(price_text)
                        if found_price > 0:
                            price = found_price
                            break
                        price_container = price_container.parent
                
                # 查找圖片
                img_elem = link.find('img')
                image_url = None
                if img_elem:
                    image_url = img_elem.get('src') or img_elem.get('data-src')
                    if image_url and not image_url.startswith('http'):
                        image_url = urllib.parse.urljoin(self.base_url, image_url)
                
                # 庫存狀態 - AUTOBUY通常顯示有庫存的產品
                in_stock = True
                
                # 檢查是否包含缺貨關鍵字
                full_text = link.get_text().lower()
                if any(keyword in full_text for keyword in ['缺貨', '售完', '無庫存', '停產']):
                    in_stock = False
                
                # 檢查是否為組合商品
                is_bundle = self._is_bundle_product(product_name)
                
                product_data = {
                    'product_name': product_name,
                    'price': price,
                    'image_url': image_url,
                    'url': product_url,  # 修正欄位名稱
                    'in_stock': in_stock,
                    'store': self.store_name,
                    'is_bundle': is_bundle
                }
                
                products.append(product_data)
                print(f"AutoBuy: 解析產品 - {product_name[:50]}... - NT${price}")
                
            except Exception as e:
                print(f"AutoBuy: 解析產品連結時出錯: {e}")
                continue
        
        print(f"AutoBuy: 總共解析到 {len(products)} 個有效產品")
        return products
    
    def _extract_price_from_text(self, text: str) -> float:
        """從文本中提取價格"""
        try:
            # 查找價格模式
            price_patterns = [
                r'\$\s*([\d,]+)',          # $1,234
                r'NT\$\s*([\d,]+)',        # NT$1,234
                r'＄\s*([\d,]+)',          # ＄1,234
                r'([\d,]+)\s*元',          # 1,234元
                r'價格[：:]\s*([\d,]+)',   # 價格：1234
                r'售價[：:]\s*([\d,]+)',   # 售價：1234
                r'([\d,]+)(?=\s*$)',       # 純數字（行尾）
            ]
            
            for pattern in price_patterns:
                matches = re.findall(pattern, text)
                if matches:
                    # 取第一個匹配的價格
                    price_str = matches[0].replace(',', '')
                    price = float(price_str)
                    if price > 100:  # 合理的價格範圍
                        return price
            
            return 0
            
        except Exception:
            return 0
    

    
    async def search_products(self, product_name: str, standalone_only: bool = False) -> List[Product]:
        """搜尋產品"""
        try:
            search_url = self._build_search_url(product_name)
            print(f"AutoBuy搜尋URL: {search_url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Referer': 'https://www.autobuy.tw/'
            }
            
            timeout = aiohttp.ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(search_url, headers=headers) as response:
                    if response.status == 200:
                        content = await response.text()
                        soup = BeautifulSoup(content, 'html.parser')
                        
                        print(f"AutoBuy: 頁面長度 {len(content)} 字符")
                        
                        # 解析產品列表
                        product_data_list = self._parse_product_list(soup)
                        
                        # 過濾組合商品（如果需要）
                        if standalone_only:
                            filtered_count = 0
                            original_count = len(product_data_list)
                            product_data_list = [p for p in product_data_list if not p.get('is_bundle', False)]
                            filtered_count = original_count - len(product_data_list)
                            if filtered_count > 0:
                                print(f"AutoBuy: 過濾了 {filtered_count} 個組合商品")
                        
                        # 轉換為Product物件
                        products = []
                        for data in product_data_list:
                            try:
                                product = Product(**data)
                                products.append(product)
                            except Exception as e:
                                print(f"AutoBuy: 創建Product物件時出錯: {e}, 數據: {data}")
                                continue
                        
                        return products
                    else:
                        print(f"AutoBuy: HTTP錯誤 {response.status}")
                        return []
                        
        except Exception as e:
            print(f"AutoBuy: 搜尋產品時出錯: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _is_bundle_product(self, product_name: str) -> bool:
        """檢查是否為組合商品"""
        if not product_name:
            return False
            
        product_name_lower = product_name.lower()
        
        # AUTOBUY組合商品標示
        bundle_indicators = [
            '套裝', '組合', '搭配', '搭機', '搭購',
            '限搭', '組裝價', '合購', '優惠組', '超值組',
            '整機', '套餐', '方案', '組合包', '大組包',
            '電競機', '電腦主機', '桌機', '筆電',
            '筆記型電腦', 'laptop', 'notebook',
            '組合價', '特惠組', '精選組', '豪華組',
            '買送', '贈送', '加購', '含', '附',
            '平台', '主機板平台', '處理器平台',
            '水冷獸', '水冷獨顯', '獨顯水冷',
            'mpk',  # AMD MPK (Multi-Pack Kit) 通常是組合包
            '經濟組', '標準組', '進階組', '旗艦組',
            '入門組', '基本組', '完整組', '全配組',
            '限量組', '限定組', '專業組', '商務組'
        ]
        
        # 檢查明確的組合標示
        for indicator in bundle_indicators:
            if indicator in product_name_lower:
                return True
        
        # 檢查加號組合模式
        if '+' in product_name or '＋' in product_name:
            # 計算+號數量，多個+號通常表示組合商品
            plus_count = product_name.count('+') + product_name.count('＋')
            if plus_count >= 2:
                return True  # 多個+號幾乎肯定是組合商品
            
            # 檢查是否為型號後綴的+（如NITRO+, TI+等）
            if re.search(r'(nitro|gaming|oc|ti|super|xt|gre|steel|legend|taichi|prime)\s*\+\s*?(?:\s|$)', product_name, re.IGNORECASE):
                # 這可能是型號的一部分，但還需要進一步檢查
                # 如果+號後面還有其他硬體組件，那就是組合商品
                if re.search(r'(nitro|gaming|oc|ti|super|xt|gre|steel|legend|taichi|prime)\s*\+.*(?:主機板|記憶體|硬碟|電源|螢幕|cpu|處理器)', product_name, re.IGNORECASE):
                    return True
            else:
                # 檢查是否為組合商品的+（包含其他硬體組件）
                combo_patterns = [
                    r'\+.*(?:主機板|mb|motherboard|b760|b850|z790|x670|x870)',
                    r'\+.*(?:記憶體|ram|memory|ddr4|ddr5)',
                    r'\+.*(?:硬碟|ssd|hdd|storage)',
                    r'\+.*(?:電源|psu|power)',
                    r'\+.*(?:螢幕|monitor|顯示器)',
                    r'\+.*(?:鍵盤|keyboard)',
                    r'\+.*(?:滑鼠|mouse)',
                    r'\+.*(?:cpu|處理器|intel|amd|i5|i7|i9|ryzen)',
                    r'\+.*(?:散熱器|cooler|風扇)',
                    r'\+.*(?:機殼|case)',
                    r'\+.*(?:華擎|asus|msi|技嘉|微星|gigabyte|asrock)',
                    r'(?:主機板|記憶體|硬碟|電源|螢幕|鍵盤|滑鼠|cpu|散熱器|機殼|intel|amd|i5|i7|i9|ryzen).*\+'
                ]
                
                for pattern in combo_patterns:
                    if re.search(pattern, product_name, re.IGNORECASE):
                        return True
        
        # 檢查數量指示詞（表示多件商品）
        quantity_patterns = [
            r'\d+件', r'\d+組', r'\d+套',
            r'第\d+件', r'兩件', r'三件', r'四件',
            r'雙.*組合', r'三.*組合', r'四.*組合'
        ]
        
        for pattern in quantity_patterns:
            if re.search(pattern, product_name, re.IGNORECASE):
                return True
        
        return False 