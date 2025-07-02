from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class Product(BaseModel):
    """單一產品資料模型"""
    store: str
    product_name: str
    price: float
    url: str
    in_stock: bool
    currency: str = "TWD"
    image_url: Optional[str] = None
    specifications: Optional[str] = None
    is_bundle: bool = False  # 是否為組合商品/專案商品

class SearchResult(BaseModel):
    """搜尋結果模型"""
    product: str
    timestamp: datetime
    results: List[Product]
    cache_expires: datetime
    total_found: int
    successful_stores: List[str]
    failed_stores: List[str]

class SearchResponse(BaseModel):
    """API 回應模型"""
    success: bool
    message: str
    data: Optional[SearchResult] = None
    error: Optional[str] = None 