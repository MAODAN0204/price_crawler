import urllib.parse
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from app.models.product import Product
from .base_scraper import BaseScraper

class DTSourceScraper(BaseScraper):
    """德源電腦爬蟲"""
    
    def __init__(self):
        super().__init__("德源電腦")
        self.base_url = "https://www.mypc.com.tw"  # 正確的德源電腦網址
        self.search_url = f"{self.base_url}/product.php"
    
    def _build_search_url(self, product_name: str) -> str:
        """建立搜尋URL"""
        # 德源電腦的正確搜尋參數格式
        params = {
            'act': 'search',
            'keywords': product_name
        }
        
        query_string = urllib.parse.urlencode(params, encoding='utf-8')
        return f"{self.search_url}?{query_string}"
    
    def _check_dtsource_stock_status(self, product_name: str) -> bool:
        """德源電腦專用的庫存狀態檢查"""
        if not product_name:
            return False
        
        # 德源電腦特有的缺貨標示格式
        dtsource_out_of_stock_patterns = [
            '已售完',
            '請勿下單',
            '僅提供報價',
            '已售完 請勿下單 僅提供報價',
            '缺貨',
            '停產',
            '暫停供應',
            '暫無庫存',
            '預購',
            '到貨通知',
            '客定產品',
            '停售'
        ]
        
        # 檢查產品名稱是否包含任何缺貨標示
        for pattern in dtsource_out_of_stock_patterns:
            if pattern in product_name:
                print(f"DTSource: 檢測到缺貨標示 '{pattern}' 在產品: {product_name[:50]}...")
                return False
        
        # 使用正則表達式檢查括號內的狀態說明
        import re
        bracket_patterns = [
            r'\(.*已售完.*\)',
            r'\(.*請勿下單.*\)',
            r'\(.*僅提供報價.*\)',
            r'\(.*缺貨.*\)',
            r'\(.*停產.*\)',
            r'\(.*暫停.*\)',
            r'（.*已售完.*）',
            r'（.*請勿下單.*）',
            r'（.*僅提供報價.*）',
            r'（.*缺貨.*）'
        ]
        
        for pattern in bracket_patterns:
            if re.search(pattern, product_name):
                print(f"DTSource: 檢測到括號內缺貨標示在產品: {product_name[:50]}...")
                return False
        
        return True
    
    def _is_bundle_only_product(self, html_content: str, product_name: str) -> bool:
        """檢查是否為合購限定商品（不單獨販售）"""
        if not html_content:
            return False
        
        # 德源電腦合購限定標示
        bundle_only_indicators = [
            '合購價',
            '限搭組裝機出貨',
            '需限定規格',
            '限搭組裝機',
            '不單獨販售',
            '組裝機專用',
            '搭機價',
            '組合價',
            '組裝價',
            '限組整機',
            '限組裝機',
            '整機專用'
        ]
        
        # 檢查HTML內容是否包含合購限定標示
        html_lower = html_content.lower()
        product_lower = product_name.lower() if product_name else ""
        
        for indicator in bundle_only_indicators:
            if indicator in html_content or indicator in product_name:
                print(f"DTSource: 檢測到合購限定標示 '{indicator}' 在產品: {product_name[:50]}...")
                return True
        
        # 檢查特定的HTML結構標示
        import re
        bundle_patterns = [
            r'合購價.*?限搭組裝機',
            r'限搭.*?出貨',
            r'需.*?限定規格',
            r'不.*?單獨.*?販售',
            r'組裝價.*?限組整機',
            r'限組.*?整機',
            r'組裝價.*?\(.*?限.*?\)',
            r'限.*?組裝機.*?出貨'
        ]
        
        for pattern in bundle_patterns:
            if re.search(pattern, html_content, re.IGNORECASE):
                print(f"DTSource: 檢測到合購限定模式 '{pattern}' 在產品: {product_name[:50]}...")
                return True
        
        return False

    async def search_products(self, product_name: str, check_bundle_only: bool = True) -> List[Product]:
        """搜尋產品"""
        try:
            search_url = self._build_search_url(product_name)
            html_content = await self._fetch_page(search_url)
            
            if not html_content:
                return []
            
            soup = self._parse_html(html_content)
            raw_products = self._parse_product_list(soup)
            
            products = []
            for raw_product in raw_products:
                try:
                    # 如果需要檢查合購限定商品，則獲取產品詳細頁面
                    is_bundle_only = False
                    if check_bundle_only and raw_product.get('url'):
                        try:
                            product_detail_html = await self._fetch_page(raw_product['url'])
                            if product_detail_html:
                                is_bundle_only = self._is_bundle_only_product(product_detail_html, raw_product['name'])
                        except Exception as e:
                            print(f"DTSource: 無法檢查產品詳細頁面 {raw_product['url']}: {e}")
                    
                    # 如果是合購限定商品，跳過此產品
                    if is_bundle_only:
                        print(f"DTSource: 跳過合購限定商品: {raw_product['name'][:50]}...")
                        continue
                    
                    product = Product(
                        store=self.store_name,
                        product_name=raw_product['name'],
                        price=raw_product['price'],
                        url=raw_product['url'],
                        in_stock=raw_product['in_stock'],
                        currency="TWD",
                        image_url=raw_product.get('image_url'),
                        specifications=raw_product.get('specifications')
                    )
                    products.append(product)
                except Exception as e:
                    print(f"Error creating product object: {e}")
                    continue
            
            return products
            
        except Exception as e:
            print(f"Error scraping DTSource: {e}")
            return []
    
    def _parse_product_list(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """解析德源電腦產品列表"""
        products = []
        
        # 根據實際分析，德源電腦使用 div.item 作為產品容器
        product_containers = soup.find_all('div', class_='item')
        
        print(f"DTSource: 找到 {len(product_containers)} 個產品容器")
        
        for container in product_containers:
            try:
                # 查找產品連結 (第一個 a 標籤)
                link_element = container.find('a', href=True)
                if not link_element:
                    continue
                
                # 建立完整URL
                product_url = link_element.get('href', '')
                if product_url:
                    if not product_url.startswith('http'):
                        if product_url.startswith('/'):
                            product_url = self.base_url + product_url
                        else:
                            product_url = self.base_url + '/' + product_url
                
                # 從圖片的 alt 屬性取得產品名稱 (這是德源電腦的實際結構)
                img_element = container.find('img')
                product_name = ""
                image_url = None
                
                if img_element:
                    # 產品名稱在 alt 屬性中
                    product_name = img_element.get('alt', '').strip()
                    
                    # 圖片URL
                    img_src = img_element.get('src', '')
                    if img_src:
                        if not img_src.startswith('http'):
                            if img_src.startswith('/'):
                                image_url = self.base_url + img_src
                            else:
                                image_url = self.base_url + '/' + img_src
                        else:
                            image_url = img_src
                
                # 如果沒有從 alt 取得名稱，嘗試從連結文字取得
                if not product_name:
                    product_name = link_element.get_text(strip=True)
                
                # 不要清理產品名稱中的庫存狀態資訊，保留完整標題用於庫存判斷
                if not product_name:
                    continue
                
                # 查找價格 - 尋找包含 $ 符號的文字
                price = 0
                price_texts = container.find_all(text=lambda text: text and '$' in str(text))
                
                for price_text in price_texts:
                    if '$' in str(price_text):
                        extracted_price = self._extract_price(str(price_text).strip())
                        if extracted_price and extracted_price > 0:
                            price = extracted_price
                            break
                
                if price <= 0:
                    continue
                
                # 使用德源電腦專用的庫存檢查邏輯
                in_stock = self._check_dtsource_stock_status(product_name)
                
                # 清理產品名稱用於顯示（移除庫存狀態標示）
                display_name = self._clean_dtsource_product_name(product_name)
                
                products.append({
                    'name': display_name,
                    'price': price,
                    'url': product_url,
                    'in_stock': in_stock,
                    'image_url': image_url,
                    'specifications': None
                })
                
                stock_status = "有庫存" if in_stock else "無庫存"
                print(f"DTSource: 解析產品 - {display_name[:50]}... - NT${price:,} - {stock_status}")
                
            except Exception as e:
                print(f"DTSource: 解析產品容器時發生錯誤: {e}")
                continue
        
        print(f"DTSource: 總共解析到 {len(products)} 個有效產品")
        return products
    
    def _clean_dtsource_product_name(self, name: str) -> str:
        """清理德源電腦產品名稱，移除庫存狀態標示"""
        if not name:
            return ""
        
        import re
        
        # 移除德源電腦特有的庫存狀態標示
        patterns_to_remove = [
            r'\s*-\s*\(已售完.*?\)',  # - (已售完 請勿下單 僅提供報價)
            r'\s*-\s*（已售完.*?）',  # - （已售完 請勿下單 僅提供報價）
            r'\(已售完.*?\)',        # (已售完 請勿下單 僅提供報價)
            r'（已售完.*?）',        # （已售完 請勿下單 僅提供報價）
            r'\s*-\s*\(缺貨.*?\)',
            r'\s*-\s*\(停產.*?\)',
            r'\s*-\s*\(暫停.*?\)',
            r'\s*-\s*\(預購.*?\)',
            r'\s*-\s*\(客定.*?\)',
        ]
        
        cleaned_name = name
        for pattern in patterns_to_remove:
            cleaned_name = re.sub(pattern, '', cleaned_name, flags=re.IGNORECASE)
        
        # 移除多餘的空格和特殊字符
        cleaned_name = ' '.join(cleaned_name.split())
        
        return cleaned_name.strip() 