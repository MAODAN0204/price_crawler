import re
from typing import Optional

class PriceFormatter:
    """價格格式化工具類"""
    
    @staticmethod
    def extract_price(price_text: str) -> Optional[float]:
        """從文字中提取價格數字"""
        if not price_text:
            return None
        
        # 移除常見的貨幣符號和文字
        cleaned = re.sub(r'[NT$￥元,，\s]', '', str(price_text))
        
        # 提取數字（包含小數點）
        price_match = re.search(r'(\d+(?:\.\d+)?)', cleaned)
        
        if price_match:
            try:
                return float(price_match.group(1))
            except ValueError:
                return None
        
        return None
    
    @staticmethod
    def format_price(price: float, currency: str = "TWD") -> str:
        """格式化價格顯示"""
        if currency == "TWD":
            return f"NT$ {price:,.0f}"
        else:
            return f"{price:,.2f} {currency}"
    
    @staticmethod
    def is_valid_price(price: Optional[float]) -> bool:
        """檢查價格是否有效"""
        return price is not None and price > 0
    
    @staticmethod
    def normalize_product_name(name: str) -> str:
        """標準化產品名稱"""
        if not name:
            return ""
        
        # 移除多餘空格
        normalized = re.sub(r'\s+', ' ', name.strip())
        
        # 統一常見縮寫
        replacements = {
            'GeForce': 'GTX',
            'Intel Core': 'Intel',
            'AMD Ryzen': 'AMD',
            'Kingston': 'Kingston',
            'Corsair': 'Corsair'
        }
        
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        
        return normalized 