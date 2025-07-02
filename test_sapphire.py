#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import sys
import os

# 添加專案根目錄到路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.scrapers.sapphire import SapphireScraper

async def test_sapphire_scraper():
    """測試藍寶石爬蟲"""
    
    print("=== 測試藍寶石官網爬蟲 ===")
    
    # 啟用詳細日誌
    import logging
    logging.basicConfig(level=logging.INFO)
    
    scraper = SapphireScraper()
    
    # 測試搜尋
    test_queries = [
        "9070"
    ]
    
    for query in test_queries:
        print(f"\n--- 測試搜尋: {query} ---")
        
        try:
            # 使用async with來確保正確的會話管理
            async with scraper:
                products = await scraper.search_products(query, max_results=10)
                
                print(f"找到 {len(products)} 個產品:")
                
                for i, product in enumerate(products, 1):
                    print(f"\n{i}. {product.name}")
                    print(f"   價格: NT${product.price}")
                    print(f"   庫存: {'✅ 有庫存' if product.stock_status == '有庫存' else '❌ 無庫存' if product.stock_status == '無庫存' else '❓ 需確認庫存'}")
                    print(f"   網址: {product.url}")
                    if product.image_url:
                        print(f"   圖片: {product.image_url}")
        
        except Exception as e:
            print(f"搜尋失敗: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n=== 測試完成 ===")

if __name__ == "__main__":
    asyncio.run(test_sapphire_scraper()) 