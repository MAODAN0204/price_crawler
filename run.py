#!/usr/bin/env python3
"""
電腦產品比價系統啟動腳本
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def main():
    """主要啟動函數"""
    print("🚀 電腦產品比價系統啟動程式")
    print("=" * 50)
    
    # 檢查當前目錄
    current_dir = Path.cwd()
    print(f"當前目錄: {current_dir}")
    
    # 檢查是否在正確的專案目錄
    if not (current_dir / "app" / "main.py").exists():
        print("❌ 錯誤：請在 price_crawler 專案根目錄執行此腳本")
        sys.exit(1)
    
    # 檢查Python套件
    print("\n📦 檢查套件安裝狀態...")
    try:
        import fastapi, streamlit, aiohttp, pandas
        from bs4 import BeautifulSoup  # beautifulsoup4的正確import
        print("✅ 所有必要套件已安裝")
    except ImportError as e:
        print(f"❌ 缺少套件: {e}")
        print("請執行: pip install -r requirements.txt")
        sys.exit(1)
    
    print("\n請選擇啟動模式:")
    print("1. 完整系統 (API + 網頁介面)")
    print("2. 僅啟動 API")
    print("3. 僅啟動網頁介面")
    print("4. 測試模式")
    print("5. 退出")
    
    while True:
        choice = input("\n請選擇 (1-5): ").strip()
        
        if choice == "1":
            start_full_system()
            break
        elif choice == "2":
            start_api_only()
            break
        elif choice == "3":
            start_streamlit_only()
            break
        elif choice == "4":
            run_tests()
            break
        elif choice == "5":
            print("👋 再見！")
            sys.exit(0)
        else:
            print("❌ 無效選擇，請輸入 1-5")

def start_full_system():
    """啟動完整系統"""
    print("\n🚀 啟動完整系統...")
    
    try:
        # 啟動API
        print("📡 啟動 FastAPI 後端...")
        api_process = subprocess.Popen([
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ])
        
        # 等待API啟動
        print("⏳ 等待API啟動...")
        time.sleep(5)
        
        # 啟動Streamlit
        print("🌐 啟動 Streamlit 前端...")
        streamlit_process = subprocess.Popen([
            sys.executable, "-m", "streamlit",
            "run", "app/streamlit_app.py",
            "--server.port", "8501"
        ])
        
        print("\n✅ 系統啟動成功！")
        print("📡 API 文件: http://localhost:8000/docs")
        print("🌐 網頁介面: http://localhost:8501")
        print("\n按 Ctrl+C 停止服務")
        
        # 等待中斷
        try:
            api_process.wait()
            streamlit_process.wait()
        except KeyboardInterrupt:
            print("\n🛑 停止服務...")
            api_process.terminate()
            streamlit_process.terminate()
            
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")

def start_api_only():
    """僅啟動API"""
    print("\n📡 啟動 FastAPI 後端...")
    
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n🛑 API 服務已停止")

def start_streamlit_only():
    """僅啟動Streamlit"""
    print("\n🌐 啟動 Streamlit 前端...")
    print("⚠️  請確保 API 服務在 http://localhost:8000 運行")
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit",
            "run", "app/streamlit_app.py"
        ])
    except KeyboardInterrupt:
        print("\n🛑 Streamlit 服務已停止")

def run_tests():
    """執行測試"""
    print("\n🧪 執行基本測試...")
    
    try:
        # 測試import
        print("1. 測試模組導入...")
        from app.config import Config
        from app.models.product import Product
        from app.utils.cache import CacheManager
        from app.scrapers.coolpc import CoolPCScraper
        print("   ✅ 模組導入成功")
        
        # 測試配置
        print("2. 測試配置...")
        config = Config()
        print(f"   ✅ API端口: {config.API_PORT}")
        print(f"   ✅ 快取時間: {config.CACHE_EXPIRE_MINUTES} 分鐘")
        
        # 測試快取
        print("3. 測試快取管理...")
        cache = CacheManager()
        cache.set("test", {"data": "test"})
        result = cache.get("test")
        assert result is not None
        print("   ✅ 快取功能正常")
        
        # 測試爬蟲初始化
        print("4. 測試爬蟲初始化...")
        scraper = CoolPCScraper()
        print(f"   ✅ 爬蟲 '{scraper.store_name}' 初始化成功")
        
        print("\n🎉 所有測試通過！")
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 