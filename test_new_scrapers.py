#!/usr/bin/env python3
"""測試新爬蟲模組"""

import asyncio
import sys
import os

# 添加專案根目錄到 Python 路徑
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app.scrapers.sanjing import SanjingScraper
from app.scrapers.pchome import PChomeScraper
from app.scrapers.momo import MomoScraper
from app.scrapers.gh3c import GH3CScraper

async def test_scraper(scraper_class, test_query="RX 9070"):
    """測試單個爬蟲"""
    print(f"\n{'='*50}")
    print(f"測試 {scraper_class.__name__}")
    print(f"{'='*50}")
    
    try:
        async with scraper_class() as scraper:
            print(f"🔍 搜尋關鍵字: {test_query}")
            products = await scraper.search_products(test_query)
            
            print(f"📊 找到 {len(products)} 個產品:")
            
            if products:
                # 顯示前5個產品
                for i, product in enumerate(products[:5], 1):
                    stock_status = "✅ 有庫存" if product.in_stock else "❌ 無庫存"
                    print(f"{i}. {product.product_name}")
                    print(f"   💰 價格: NT${product.price:,.0f}")
                    print(f"   📦 庫存: {stock_status}")
                    print(f"   🔗 連結: {product.url}")
                    print(f"   🏪 店家: {product.store}")
                    print()
                
                if len(products) > 5:
                    print(f"... 還有 {len(products) - 5} 個產品")
            else:
                print("❌ 沒有找到任何產品")
    
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()

async def test_all_scrapers():
    """測試所有新爬蟲"""
    print("🚀 開始測試新增的爬蟲模組")
    print("測試關鍵字: RX 9070")
    
    scrapers_to_test = [
        SanjingScraper,   # 三井3C購物網
        PChomeScraper,    # PChome 24h購物
        MomoScraper,      # momo購物網
        GH3CScraper,      # 良興電子
    ]
    
    for scraper_class in scrapers_to_test:
        await test_scraper(scraper_class)
        await asyncio.sleep(2)  # 避免請求太頻繁
    
    print(f"\n{'='*50}")
    print("🎉 所有爬蟲測試完成！")
    print(f"{'='*50}")

async def test_specific_scraper(scraper_name):
    """測試特定爬蟲"""
    scraper_mapping = {
        "sanjing": SanjingScraper,
        "pchome": PChomeScraper,
        "momo": MomoScraper,
        "gh3c": GH3CScraper,
    }
    
    if scraper_name.lower() in scraper_mapping:
        await test_scraper(scraper_mapping[scraper_name.lower()])
    else:
        print(f"❌ 找不到爬蟲: {scraper_name}")
        print(f"可用的爬蟲: {', '.join(scraper_mapping.keys())}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 測試特定爬蟲
        scraper_name = sys.argv[1]
        asyncio.run(test_specific_scraper(scraper_name))
    else:
        # 測試所有爬蟲
        asyncio.run(test_all_scrapers()) 