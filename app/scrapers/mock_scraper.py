from typing import List, Dict, Any
from app.models.product import Product
from .base_scraper import BaseScraper
import asyncio

class MockScraper(BaseScraper):
    """模擬爬蟲，用於測試和展示"""
    
    def __init__(self):
        super().__init__("測試商店")
        self.base_url = "https://example.com"
        
        # 模擬產品數據
        self.mock_products = [
            # RTX 40系列
            {
                "name": "ASUS ROG RTX 4090 24GB GDDR6X",
                "price": 45000,
                "url": "https://example.com/rtx4090",
                "in_stock": True,
                "specs": "24GB GDDR6X, 2520MHz"
            },
            {
                "name": "MSI RTX 4080 SUPER 16GB Gaming X",
                "price": 35000,
                "url": "https://example.com/rtx4080super",
                "in_stock": True,
                "specs": "16GB GDDR6X, 2550MHz"
            },
            {
                "name": "GIGABYTE RTX 4070 12GB WINDFORCE",
                "price": 22000,
                "url": "https://example.com/rtx4070",
                "in_stock": True,
                "specs": "12GB GDDR6X, 2475MHz"
            },
            {
                "name": "ASUS TUF RTX 4060 Ti 16GB",
                "price": 18000,
                "url": "https://example.com/rtx4060ti",
                "in_stock": True,
                "specs": "16GB GDDR6, 2540MHz"
            },
            {
                "name": "MSI RTX 4060 8GB VENTUS 2X",
                "price": 12000,
                "url": "https://example.com/rtx4060",
                "in_stock": True,
                "specs": "8GB GDDR6, 2460MHz"
            },
            
            # RTX 30系列
            {
                "name": "ASUS ROG RTX 3080 10GB STRIX",
                "price": 28000,
                "url": "https://example.com/rtx3080",
                "in_stock": True,
                "specs": "10GB GDDR6X, 1935MHz"
            },
            {
                "name": "MSI RTX 3070 8GB Gaming X Trio",
                "price": 20000,
                "url": "https://example.com/rtx3070",
                "in_stock": True,
                "specs": "8GB GDDR6, 1815MHz"
            },
            {
                "name": "GIGABYTE RTX 3060 Ti 8GB EAGLE",
                "price": 15000,
                "url": "https://example.com/rtx3060ti",
                "in_stock": True,
                "specs": "8GB GDDR6, 1695MHz"
            },
            
            # RTX 50系列 (最新)
            {
                "name": "ASUS ROG RTX 5090 32GB STRIX",
                "price": 85000,
                "url": "https://example.com/rtx5090",
                "in_stock": True,
                "specs": "32GB GDDR7, 2610MHz"
            },
            {
                "name": "MSI RTX 5080 16GB Gaming X Trio",
                "price": 55000,
                "url": "https://example.com/rtx5080",
                "in_stock": True,
                "specs": "16GB GDDR7, 2295MHz"
            },
            {
                "name": "GIGABYTE RTX 5070 Ti 16GB WINDFORCE",
                "price": 38000,
                "url": "https://example.com/rtx5070ti",
                "in_stock": True,
                "specs": "16GB GDDR7, 2390MHz"
            },
            {
                "name": "ASUS TUF RTX 5070 12GB",
                "price": 28000,
                "url": "https://example.com/rtx5070",
                "in_stock": True,
                "specs": "12GB GDDR7, 2160MHz"
            },
            
            # RX系列 (AMD)
            {
                "name": "GIGABYTE RX 9070 WINDFORCE OC 16GB",
                "price": 23000,
                "url": "https://example.com/rx9070windforce",
                "in_stock": True,
                "specs": "16GB GDDR6, 2565MHz"
            },
            {
                "name": "MSI RX 9070 20GB Gaming Trio X (概念產品)",
                "price": 24000,
                "url": "https://example.com/rx9070",
                "in_stock": True,
                "specs": "20GB GDDR6, 2450MHz"
            },
            {
                "name": "ASUS RX 9070 XT 16GB STRIX Gaming (未來款)",
                "price": 26000,
                "url": "https://example.com/rx9070xt",
                "in_stock": True,
                "specs": "16GB GDDR6, 2680MHz"
            },
            
            # 其他配件
            {
                "name": "Intel Core i9-14900K 處理器",
                "price": 15500,
                "url": "https://example.com/i9-14900k",
                "in_stock": True,
                "specs": "24核心, 5.6GHz"
            },
            {
                "name": "AMD Ryzen 9 7950X3D 處理器",
                "price": 18000,
                "url": "https://example.com/ryzen9-7950x3d",
                "in_stock": True,
                "specs": "16核心, 5.7GHz"
            }
        ]
    
    def _build_search_url(self, product_name: str) -> str:
        """建立搜尋URL"""
        return self.base_url
    
    async def search_products(self, product_name: str) -> List[Product]:
        """搜尋產品"""
        try:
            # 模擬網路延遲
            await asyncio.sleep(0.1)
            
            results = []
            search_term = product_name.lower().replace(" ", "").replace("-", "")
            
            for mock_product in self.mock_products:
                product_name_clean = mock_product["name"].lower().replace(" ", "").replace("-", "")
                
                # 檢查產品名稱是否包含搜尋關鍵字
                if search_term in product_name_clean:
                    product = Product(
                        store=self.store_name,
                        product_name=mock_product["name"],
                        price=mock_product["price"],
                        url=mock_product["url"],
                        in_stock=mock_product["in_stock"],
                        currency="TWD",
                        specifications=mock_product["specs"]
                    )
                    results.append(product)
            
            return results
            
        except Exception as e:
            print(f"Error in mock scraper: {e}")
            return []
    
    def _parse_product_list(self, soup) -> List[Dict[str, Any]]:
        """解析產品列表 - 模擬爬蟲不需要實作"""
        return [] 