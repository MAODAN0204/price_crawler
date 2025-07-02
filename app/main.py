import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from app.config import Config
from app.models.product import Product, SearchResult, SearchResponse
from app.utils.cache import CacheManager
from app.utils.product_matcher import ProductMatcher
from app.scrapers.coolpc import CoolPCScraper
from app.scrapers.dtsource import DTSourceScraper
from app.scrapers.autobuy import AutobuyScraper
from app.scrapers.sinya import SinyaScraper
from app.scrapers.sapphire import SapphireScraper
from app.scrapers.sunfar import SunfarScraper
# from app.scrapers.sanjing import SanjingScraper
from app.scrapers.pchome import PChomeScraper
# from app.scrapers.momo import MomoScraper
# from app.scrapers.gh3c import GH3CScraper

# 初始化FastAPI應用程式
app = FastAPI(
    title="電腦產品比價系統 API",
    description="即時搜尋台灣電腦產品價格的比價系統",
    version="1.0.0"
)

# 添加CORS中介軟體
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化元件
config = Config()
cache_manager = CacheManager()
product_matcher = ProductMatcher()

# 爬蟲映射
SCRAPERS = {
    "dtsource": DTSourceScraper,   # 德源電腦
    "autobuy": AutobuyScraper,     # AUTOBUY購物中心
    "sinya": SinyaScraper,         # 欣亞數位
    "sapphire": SapphireScraper,   # 藍寶石官網
    "sunfar": SunfarScraper,       # 順發電腦
    # "sanjing": SanjingScraper,     # 三井3C購物網 - 暫時停用
    "pchome": PChomeScraper,       # PChome 24h購物
    # "momo": MomoScraper,           # momo購物網 - 暫時停用
    # "gh3c": GH3CScraper,           # 良興電子 - 暫時停用
    "coolpc": CoolPCScraper,       # 原價屋
}

@app.get("/")
async def root():
    """根路徑"""
    return {
        "message": "電腦產品比價系統 API",
        "version": "1.0.0",
        "endpoints": {
            "search": "/api/search?product={產品名稱}",
            "health": "/health",
            "cache_stats": "/api/cache/stats"
        }
    }

@app.get("/health")
async def health_check():
    """健康檢查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "scrapers": list(SCRAPERS.keys())
    }

@app.get("/api/cache/stats")
async def get_cache_stats():
    """取得快取統計資訊"""
    return cache_manager.get_stats()

@app.delete("/api/cache")
async def clear_cache():
    """清空快取"""
    cache_manager.clear()
    return {"message": "快取已清空"}

async def scrape_single_store(scraper_class, product_name: str, standalone_only: bool = False) -> List[Product]:
    """搜尋單一商店"""
    try:
        async with scraper_class() as scraper:
            print(f"正在搜尋商品型號 {product_name} - {scraper_class.__name__}")
            
            # 對於德源電腦，支援過濾合購限定商品
            if scraper_class.__name__ == 'DTSourceScraper' and hasattr(scraper, 'search_products'):
                products = await scraper.search_products(product_name, check_bundle_only=standalone_only)
            # 對於欣亞數位，支援過濾組合商品
            elif scraper_class.__name__ == 'SinyaScraper' and hasattr(scraper, 'search_products'):
                products = await scraper.search_products(product_name, standalone_only=standalone_only)
            # 對於PChome，支援過濾組合包商品
            elif scraper_class.__name__ == 'PChomeScraper' and hasattr(scraper, 'search_products'):
                products = await scraper.search_products(product_name, standalone_only=standalone_only)
            # 對於原價屋，支援過濾專案商品
            elif scraper_class.__name__ == 'CoolPCScraper' and hasattr(scraper, 'search_products'):
                products = await scraper.search_products(product_name, standalone_only=standalone_only)
            else:
                products = await scraper.search_products(product_name)
                
            print(f"{scraper_class.__name__} 搜尋完成，找到 {len(products)} 個產品")
            return products
    except Exception as e:
        print(f"搜尋 {scraper_class.__name__} 時發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return []

async def scrape_all_stores(product_name: str, standalone_only: bool = False) -> Dict[str, Any]:
    """並行搜尋所有商店"""
    # 建立搜尋任務
    tasks = []
    store_names = []
    
    for store_key, scraper_class in SCRAPERS.items():
        task = scrape_single_store(scraper_class, product_name, standalone_only)
        tasks.append(task)
        store_names.append(store_key)
    
    # 並行執行
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 整理結果
    all_products = []
    successful_stores = []
    failed_stores = []
    
    for i, result in enumerate(results):
        store_name = store_names[i]
        
        if isinstance(result, Exception):
            print(f"Store {store_name} failed: {result}")
            failed_stores.append(store_name)
        elif isinstance(result, list):
            all_products.extend(result)
            if result:  # 如果有找到產品
                successful_stores.append(store_name)
            else:
                failed_stores.append(store_name)
        else:
            failed_stores.append(store_name)
    
    return {
        "products": all_products,
        "successful_stores": successful_stores,
        "failed_stores": failed_stores
    }

@app.get("/api/search", response_model=SearchResponse)
async def search_products(
    product: str = Query(..., description="要搜尋的產品名稱", min_length=2),
    sort_by: str = Query("price", description="排序方式 (price, name, store)"),
    order: str = Query("asc", description="排序順序 (asc, desc)"),
    in_stock_only: bool = Query(False, description="只顯示有庫存的商品"),
    standalone_only: bool = Query(False, description="只顯示單獨商品（排除整機/筆電）"),
    min_price: float = Query(None, description="最低價格篩選"),
    max_price: float = Query(None, description="最高價格篩選")
):
    """搜尋產品價格"""
    try:
        # 檢查快取
        cached_result = cache_manager.get(product)
        if cached_result:
            search_result = SearchResult(**cached_result)
            
            # 應用篩選和排序
            filtered_products = apply_filters_and_sort(
                search_result.results, 
                sort_by, order, in_stock_only, min_price, max_price
            )
            
            search_result.results = filtered_products
            search_result.total_found = len(filtered_products)
            
            return SearchResponse(
                success=True,
                message="從快取返回結果",
                data=search_result
            )
        
        # 執行搜尋
        scrape_results = await scrape_all_stores(product, standalone_only)
        all_products = scrape_results["products"]
        
        if not all_products:
            return SearchResponse(
                success=False,
                message="未找到相關產品",
                error="所有商店都沒有找到匹配的產品"
            )
        
        # 產品相關性過濾 - 使用較低的閾值以包含更多相關產品
        relevant_products = product_matcher.filter_relevant_products(
            product, 
            [p.model_dump() for p in all_products],
            threshold=0.2,  # 降低閾值以包含整機配置等複雜產品名稱
            standalone_only=standalone_only  # 是否只顯示單獨商品
        )
        
        # 轉換回Product物件
        filtered_products_objects = []
        for product_dict in relevant_products:
            try:
                product_obj = Product(**product_dict)
                filtered_products_objects.append(product_obj)
            except Exception as e:
                print(f"Error creating product object: {e}")
                continue
        
        # 應用篩選和排序
        final_products = apply_filters_and_sort(
            filtered_products_objects,
            sort_by, order, in_stock_only, min_price, max_price
        )
        
        # 建立搜尋結果
        current_time = datetime.now()
        cache_expires = current_time + timedelta(minutes=config.CACHE_EXPIRE_MINUTES)
        
        search_result = SearchResult(
            product=product,
            timestamp=current_time,
            results=final_products,
            cache_expires=cache_expires,
            total_found=len(final_products),
            successful_stores=scrape_results["successful_stores"],
            failed_stores=scrape_results["failed_stores"]
        )
        
        # 儲存到快取
        cache_manager.set(product, search_result.dict())
        
        return SearchResponse(
            success=True,
            message=f"找到 {len(final_products)} 個相關產品",
            data=search_result
        )
        
    except Exception as e:
        print(f"Search error: {e}")
        return SearchResponse(
            success=False,
            message="搜尋時發生錯誤",
            error=str(e)
        )

def apply_filters_and_sort(
    products: List[Product],
    sort_by: str,
    order: str,
    in_stock_only: bool,
    min_price: float = None,
    max_price: float = None
) -> List[Product]:
    """應用篩選和排序"""
    filtered = products.copy()
    
    # 庫存篩選
    if in_stock_only:
        filtered = [p for p in filtered if p.in_stock]
    
    # 價格篩選
    if min_price is not None:
        filtered = [p for p in filtered if p.price >= min_price]
    
    if max_price is not None:
        filtered = [p for p in filtered if p.price <= max_price]
    
    # 排序
    reverse = (order.lower() == "desc")
    
    if sort_by == "price":
        filtered.sort(key=lambda x: x.price, reverse=reverse)
    elif sort_by == "name":
        filtered.sort(key=lambda x: x.product_name.lower(), reverse=reverse)
    elif sort_by == "store":
        filtered.sort(key=lambda x: x.store, reverse=reverse)
    
    return filtered

# 個別爬蟲端點

# @app.get("/api/sanjing/search")
# async def search_sanjing(product: str = Query(..., description="要搜尋的產品名稱")):
#     """搜尋三井3C購物網"""
#     try:
#         async with SanjingScraper() as scraper:
#             products = await scraper.search_products(product)
#             return {"store": "三井3C", "products": [p.dict() for p in products]}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/pchome/search")
async def search_pchome(product: str = Query(..., description="要搜尋的產品名稱")):
    """搜尋PChome 24h購物"""
    try:
        async with PChomeScraper() as scraper:
            products = await scraper.search_products(product)
            return {"store": "PChome 24h", "products": [p.dict() for p in products]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# @app.get("/api/momo/search")
# async def search_momo(product: str = Query(..., description="要搜尋的產品名稱")):
#     """搜尋momo購物網"""
#     try:
#         async with MomoScraper() as scraper:
#             products = await scraper.search_products(product)
#             return {"store": "momo購物網", "products": [p.dict() for p in products]}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.get("/api/gh3c/search")
# async def search_gh3c(product: str = Query(..., description="要搜尋的產品名稱")):
#     """搜尋良興電子"""
#     try:
#         async with GH3CScraper() as scraper:
#             products = await scraper.search_products(product)
#             return {"store": "良興電子", "products": [p.dict() for p in products]}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True
    ) 