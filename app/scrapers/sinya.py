import asyncio
import aiohttp
import urllib.parse
from typing import List, Dict, Any
from bs4 import BeautifulSoup
import json
import re
from app.scrapers.base_scraper import BaseScraper
from app.models.product import Product

class SinyaScraper(BaseScraper):
    """欣亞數位爬蟲"""
    
    def __init__(self):
        super().__init__("欣亞數位")
        self.base_url = "https://www.sinya.com.tw"
        self.search_url = f"{self.base_url}/search/0"
    
    def _build_search_url(self, product_name: str) -> str:
        """建立搜尋URL"""
        # 欣亞數位的正確搜尋格式: /search/0?keyword=產品名稱
        params = {
            'keyword': product_name
        }
        
        query_string = urllib.parse.urlencode(params, encoding='utf-8')
        return f"{self.base_url}/search/0?{query_string}"
    
    def _parse_product_list(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """解析產品列表"""
        products = []
        
        try:
            # 尋找包含產品資料的JavaScript
            scripts = soup.find_all('script')
            
            for script in scripts:
                if script.string and 'this.products' in script.string:
                    script_content = script.string
                    
                    # 尋找產品JSON資料
                    # 格式: this.products = [產品資料]; 或其他變體
                    patterns = [
                        r'const\s+results\s*=\s*(\[.*?\]);',  # 實際格式: const results = [...]
                        r'this\.products\s*=\s*(\[.*?\]);',   # 原始格式
                        r'this\.products\s*=\s*(\[.*?\])',    # 沒有分號
                        r'products:\s*(\[.*?\])',             # 物件格式
                        r'\.products\s*=\s*(\[.*?\])',        # 其他變體
                        r'results\s*=\s*(\[.*?\]);',          # 簡化格式
                    ]
                    
                    match = None
                    
                    # 特殊處理：對於const results格式，使用更精確的匹配
                    if 'const results' in script_content:
                        # 找到const results行並提取完整的JSON
                        lines = script_content.split('\n')
                        for line in lines:
                            if 'const results' in line and '=' in line:
                                json_part = line.split('=', 1)[1].strip()
                                if json_part.endswith(';'):
                                    json_part = json_part[:-1]
                                print(f"欣亞數位直接提取JSON，長度: {len(json_part)}")
                                # 創建假的match物件
                                match = type('Match', (), {'group': lambda self, x: json_part})()
                                break
                    
                    # 如果特殊處理沒有找到，使用正則表達式
                    if not match:
                        for pattern in patterns:
                            match = re.search(pattern, script_content, re.DOTALL)
                            if match:
                                print(f"欣亞數位找到產品資料，使用模式: {pattern[:30]}...")
                                break
                    
                    if match:
                        products_json = match.group(1)
                        try:
                            # 首先嘗試直接解析JSON
                            try:
                                products_data = json.loads(products_json)
                                print(f"欣亞數位直接JSON解析成功")
                            except json.JSONDecodeError:
                                # 如果直接解析失敗，嘗試修復JavaScript物件字面量
                                print(f"欣亞數位直接解析失敗，嘗試修復...")
                                json_fixed = self._fix_javascript_object(products_json)
                                products_data = json.loads(json_fixed)
                                print(f"欣亞數位修復後解析成功")
                            
                            for product_data in products_data:
                                # 提取產品資訊
                                name = product_data.get('prod_title', '').strip()
                                price = self._extract_price(product_data.get('new_price', ''))
                                url = product_data.get('href', '')
                                
                                # 解碼Unicode字符（如果需要）
                                if name and '\\u' in name:
                                    try:
                                        import codecs
                                        name = codecs.decode(name, 'unicode_escape')
                                    except:
                                        pass  # 如果解碼失敗，使用原始名稱
                                
                                product_info = {
                                    'name': name,
                                    'price': price,
                                    'original_price': self._extract_price(product_data.get('old_price', '')),
                                    'url': url,
                                    'image': product_data.get('image', ''),
                                    'availability': self._check_availability(product_data),
                                    'description': product_data.get('prod_subtitle', '').strip()
                                }
                                
                                # 只添加有名稱和價格的產品
                                if name and price > 0:
                                    products.append(product_info)
                                    print(f"欣亞數位找到產品: {name[:50]}... - NT${price:,}")
                                elif name:
                                    print(f"欣亞數位跳過無價格產品: {name[:50]}...")
                                else:
                                    print("欣亞數位跳過空產品")
                            
                            break  # 找到產品資料就停止搜尋
                            
                        except json.JSONDecodeError as e:
                            print(f"欣亞數位解析產品JSON失敗: {e}")
                            continue
            
            # 如果JavaScript解析失敗，嘗試HTML解析
            if not products:
                products = self._parse_html_products(soup)
                
        except Exception as e:
            print(f"欣亞數位解析產品列表失敗: {e}")
        
        return products
    
    def _parse_html_products(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """備用的HTML產品解析方法"""
        products = []
        
        try:
            # 尋找產品容器
            product_containers = soup.find_all(['div', 'li', 'article'], 
                                             class_=lambda x: x and any(
                                                 keyword in str(x).lower() 
                                                 for keyword in ['product', 'item', 'card', 'prod']
                                             ))
            
            for container in product_containers:
                try:
                    # 提取產品名稱
                    name_elem = container.find(['h3', 'h4', 'h5', 'a'], 
                                             class_=lambda x: x and 'title' in str(x).lower())
                    if not name_elem:
                        name_elem = container.find('a', href=True)
                    
                    if name_elem:
                        name = name_elem.get_text(strip=True)
                        
                        # 提取價格
                        price_elem = container.find(['span', 'div'], 
                                                  class_=lambda x: x and 'price' in str(x).lower())
                        if not price_elem:
                            price_elem = container.find(text=re.compile(r'[\$＄][\d,]+'))
                        
                        price = 0
                        if price_elem:
                            if hasattr(price_elem, 'get_text'):
                                price_text = price_elem.get_text(strip=True)
                            else:
                                price_text = str(price_elem).strip()
                            price = self._extract_price(price_text)
                        
                        # 提取連結
                        link_elem = container.find('a', href=True)
                        url = ''
                        if link_elem:
                            href = link_elem['href']
                            url = href if href.startswith('http') else f"{self.base_url}{href}"
                        
                        if name and price > 0:
                            products.append({
                                'name': name,
                                'price': price,
                                'original_price': price,
                                'url': url,
                                'image': '',
                                'availability': '有庫存',
                                'description': ''
                            })
                            
                except Exception as e:
                    print(f"欣亞數位解析單個產品失敗: {e}")
                    continue
                    
        except Exception as e:
            print(f"欣亞數位HTML產品解析失敗: {e}")
        
        return products
    
    def _extract_price(self, price_text: str) -> int:
        """從價格文字中提取數字"""
        if not price_text:
            return 0
        
        try:
            # 移除貨幣符號和非數字字符，保留數字和逗號
            price_clean = re.sub(r'[^\d,]', '', str(price_text))
            
            if price_clean:
                # 移除逗號並轉換為整數
                return int(price_clean.replace(',', ''))
        except (ValueError, AttributeError):
            pass
        
        return 0
    
    def _check_availability(self, product_data: Dict[str, Any]) -> str:
        """檢查產品庫存狀態"""
        # 檢查是否有庫存相關資訊
        if 'stock' in product_data:
            stock = product_data['stock']
            if stock == 0 or stock == '0':
                return '缺貨'
            else:
                return '有庫存'
        
        # 檢查是否有顯示狀態
        if 'display_price_status' in product_data:
            status = product_data['display_price_status']
            if '缺貨' in str(status) or '無庫存' in str(status) or '補貨中' in str(status):
                return '缺貨'
        
        # 檢查產品名稱中是否包含缺貨指標
        product_name = product_data.get('name', '')
        if '補貨中' in product_name or '缺貨' in product_name or '售完' in product_name:
            return '缺貨'
        
        # 對於欣亞數位，搜尋結果中的產品預設需要進一步確認庫存
        # 因為欣亞的搜尋頁面不總是顯示準確的庫存狀態
        return '需確認庫存'
    
    async def _check_product_stock_detail(self, product_url: str) -> str:
        """檢查產品詳細頁面的庫存狀態"""
        try:
            html_content = await self._fetch_page(product_url)
            if html_content:
                soup = BeautifulSoup(html_content, 'html.parser')
                page_text = soup.get_text()
                
                # 優先檢查明確的缺貨指標
                out_of_stock_indicators = [
                    "補貨中", "缺貨", "無庫存", "貨到通知", "預購", "到貨通知",
                    "暫無庫存", "售完", "停售", "未上市", "貨到通知我", 
                    "暫停供應", "暫時缺貨", "等待到貨"
                ]
                for indicator in out_of_stock_indicators:
                    if indicator in page_text:
                        print(f"欣亞數位檢測到缺貨指標: {indicator}")
                        return '缺貨'
                
                # 檢查HTML元素中的缺貨狀態
                # 查找購買按鈕區域的狀態
                purchase_section = soup.find('div', class_=lambda x: x and ('purchase' in str(x).lower() or 'buy' in str(x).lower()))
                if purchase_section:
                    section_text = purchase_section.get_text()
                    if "補貨中" in section_text or "貨到通知" in section_text:
                        print(f"欣亞數位在購買區域檢測到缺貨狀態")
                        return '缺貨'
                
                # 檢查特定的缺貨按鈕或文字
                notify_buttons = soup.find_all(text=lambda text: text and ("貨到通知" in text or "補貨中" in text))
                if notify_buttons:
                    print(f"欣亞數位檢測到缺貨按鈕或文字")
                    return '缺貨'
                
                # 檢查有庫存的明確指標
                in_stock_indicators = [
                    "加入購物車", "立即結帳", "立即購買", "現貨", "庫存充足",
                    "可購買", "有庫存"
                ]
                for indicator in in_stock_indicators:
                    if indicator in page_text:
                        print(f"欣亞數位檢測到有庫存指標: {indicator}")
                        return '有庫存'
                
                # 如果沒有明確的庫存指標，檢查是否有購買相關按鈕
                buy_buttons = soup.find_all(['button', 'input', 'a'], text=lambda text: text and "購物車" in text)
                if buy_buttons:
                    print("欣亞數位找到購物車按鈕，假設有庫存")
                    return '有庫存'
                
                # 最後檢查：如果沒有任何明確指標，預設為缺貨（更保守的做法）
                print("欣亞數位無法確定庫存狀態，預設為缺貨")
                return '缺貨'
            else:
                return '缺貨'  # 無法獲取頁面時預設缺貨
        except Exception as e:
            print(f"欣亞數位檢查產品詳細庫存失敗: {e}")
            return '缺貨'  # 錯誤時預設缺貨
    
    def _fix_javascript_object(self, js_object_str: str) -> str:
        """將JavaScript物件字面量轉換為有效的JSON"""
        try:
            # 修復常見的JavaScript物件字面量問題
            fixed = js_object_str
            
            # 1. 為屬性名添加雙引號
            # 匹配 property: 格式並轉換為 "property":
            fixed = re.sub(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'"\1":', fixed)
            
            # 2. 修復單引號為雙引號
            fixed = re.sub(r"'([^']*)'", r'"\1"', fixed)
            
            # 3. 移除尾隨逗號
            fixed = re.sub(r',\s*}', '}', fixed)
            fixed = re.sub(r',\s*]', ']', fixed)
            
            # 4. 修復undefined為null
            fixed = re.sub(r'\bundefined\b', 'null', fixed)
            
            # 5. 修復空值
            fixed = re.sub(r':\s*,', ': null,', fixed)
            
            return fixed
            
        except Exception as e:
            print(f"欣亞數位修復JavaScript物件失敗: {e}")
            return js_object_str
    
    def _is_bundle_product(self, product_name: str) -> bool:
        """檢查是否為組合套裝商品"""
        # 明確的組合商品指標
        bundle_indicators = [
            '【救贖】', '【套裝】', '【組合】', '【搭配】', '【配套】', '【組裝價】',
            '套裝', '組合', '搭配', '配套', '組裝價', '超值組', '大組包',
            '救贖', '組裝機', '整機', '主機', '套餐',
            '經濟組', '標準組', '進階組', '旗艦組',
            '入門組', '基本組', '完整組', '全配組',
            '豪華組', '精選組', '專業組', '商務組'
        ]
        
        product_name_lower = product_name.lower()
        
        # 先檢查明確的組合商品指標
        for indicator in bundle_indicators:
            if indicator.lower() in product_name_lower:
                return True
        
        # 檢查是否為真正的多產品組合（用+號連接不同類型產品）
        # 但要排除產品型號中的+號（如NITRO+）
        if '+' in product_name or '＋' in product_name:
            # 檢查+號前後是否為不同類型的產品
            # 常見的組合模式：顯示卡+電源、主機板+CPU等
            combo_patterns = [
                r'[^+]*\+.*(?:電源|PSU|Power)',  # 產品+電源
                r'[^+]*\+.*(?:主機板|MB|Motherboard|主板)',  # 產品+主機板
                r'[^+]*\+.*(?:CPU|處理器)',  # 產品+CPU
                r'[^+]*\+.*(?:記憶體|RAM|Memory)',  # 產品+記憶體
                r'[^+]*\+.*(?:硬碟|SSD|HDD)',  # 產品+硬碟
                r'[^+]*\+.*(?:螢幕|Monitor|顯示器)',  # 產品+螢幕
                r'(?:電源|PSU|Power).*\+',  # 電源+產品
                r'(?:主機板|MB|Motherboard|主板).*\+',  # 主機板+產品
                r'(?:CPU|處理器).*\+',  # CPU+產品
                r'(?:記憶體|RAM|Memory).*\+',  # 記憶體+產品
                r'(?:硬碟|SSD|HDD).*\+',  # 硬碟+產品
                r'(?:螢幕|Monitor|顯示器).*\+',  # 螢幕+產品
                # 特別處理主機板品牌和型號的組合
                r'\+.*(?:華擎|ASUS|技嘉|微星|MSI|ASRock|GIGABYTE).*(?:X870|B650|Z790|B760|X670|B550|X570|Z690)',  # +主機板型號
                r'(?:華擎|ASUS|技嘉|微星|MSI|ASRock|GIGABYTE).*(?:X870|B650|Z790|B760|X670|B550|X570|Z690).*\+',  # 主機板型號+
            ]
            
            import re
            for pattern in combo_patterns:
                if re.search(pattern, product_name, re.IGNORECASE):
                    return True
            
            # 額外檢查：如果包含主機板相關關鍵字且有+號，很可能是組合
            motherboard_keywords = ['X870E', 'X870', 'B650', 'Z790', 'B760', 'X670', 'B550', 'X570', 'Z690', 'X399', 'TRX40']
            for keyword in motherboard_keywords:
                if keyword in product_name and ('+' in product_name or '＋' in product_name):
                    return True
        
        return False

    def _create_product(self, product_data: Dict[str, Any]) -> Product:
        """建立Product物件"""
        availability = product_data.get('availability', '需確認庫存')
        # 只有明確標示為 '有庫存' 時才設定為 True
        in_stock = availability == '有庫存'
        
        # 檢查是否為組合商品
        is_bundle = self._is_bundle_product(product_data['name'])
        
        return Product(
            store=self.store_name,
            product_name=product_data['name'],
            price=float(product_data['price']),
            url=product_data['url'],
            in_stock=in_stock,
            image_url=product_data.get('image', ''),
            specifications=product_data.get('description', ''),
            is_bundle=is_bundle
        )
    
    async def search_products(self, product_name: str, check_stock_detail: bool = True, standalone_only: bool = False) -> List[Product]:
        """搜尋產品的主要方法"""
        try:
            # 建立搜尋URL
            search_url = self._build_search_url(product_name)
            print(f"欣亞數位搜尋URL: {search_url}")
            
            # 發送請求
            html_content = await self._fetch_page(search_url)
            if html_content:
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # 解析產品列表
                products_data = self._parse_product_list(soup)
                
                # 轉換為Product物件
                products = []
                filtered_count = 0
                
                for product_data in products_data:
                    try:
                        # 檢查是否為組合商品
                        if standalone_only and self._is_bundle_product(product_data['name']):
                            print(f"欣亞數位過濾組合商品: {product_data['name'][:50]}...")
                            filtered_count += 1
                            continue
                        
                        # 如果需要檢查詳細庫存且有產品URL
                        if check_stock_detail and product_data.get('url'):
                            print(f"檢查產品詳細庫存: {product_data['name'][:30]}...")
                            detailed_stock = await self._check_product_stock_detail(product_data['url'])
                            product_data['availability'] = detailed_stock
                        
                        product = self._create_product(product_data)
                        products.append(product)
                    except Exception as e:
                        print(f"欣亞數位建立產品物件失敗: {e}")
                        continue
                
                if standalone_only and filtered_count > 0:
                    print(f"欣亞數位過濾了 {filtered_count} 個組合商品")
                
                print(f"欣亞數位成功解析 {len(products)} 個產品")
                return products
            else:
                print(f"欣亞數位無法獲取網頁內容")
                return []
                    
        except Exception as e:
            print(f"欣亞數位搜尋產品失敗: {e}")
            return [] 