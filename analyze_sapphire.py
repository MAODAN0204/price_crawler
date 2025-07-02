#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
from bs4 import BeautifulSoup
import re

def analyze_sapphire_site():
    """分析藍寶石官網結構"""
    
    print("=== 分析藍寶石官網結構 ===")
    
    # 測試搜尋頁面
    search_url = "https://sapphiretech.cyberbiz.co/search?q=9070"
    print(f"正在分析: {search_url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=30)
        print(f"HTTP狀態碼: {response.status_code}")
        
        if response.status_code == 200:
            html_content = response.text
            print(f"HTML內容長度: {len(html_content)}")
            
            # 檢查是否有產品資料
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 尋找產品容器
            print("\n=== 尋找產品容器 ===")
            
            # 常見的產品容器選擇器
            selectors_to_try = [
                '.product-item',
                '.product-card',
                '.product',
                '.item',
                '[data-product]',
                '.grid-item',
                '.product-listing',
                '.search-result',
                '.product-wrapper'
            ]
            
            for selector in selectors_to_try:
                products = soup.select(selector)
                if products:
                    print(f"找到 {len(products)} 個產品使用選擇器: {selector}")
                    
                    # 分析第一個產品的結構
                    if products:
                        first_product = products[0]
                        print(f"第一個產品HTML結構:")
                        print(first_product.prettify()[:500])
                        print("...")
                        break
            
            # 檢查是否有JavaScript產品數據
            print("\n=== 檢查JavaScript數據 ===")
            
            # 尋找JSON數據
            script_tags = soup.find_all('script')
            for i, script in enumerate(script_tags):
                if script.string:
                    script_content = script.string
                    
                    # 檢查是否包含產品數據
                    if any(keyword in script_content.lower() for keyword in ['product', 'item', 'search', 'result']):
                        print(f"Script {i} 可能包含產品數據:")
                        print(script_content[:300])
                        print("...\n")
                        
                        # 嘗試提取JSON
                        try:
                            # 尋找JSON格式的數據
                            json_match = re.search(r'\{.*\}', script_content)
                            if json_match:
                                json_data = json.loads(json_match.group())
                                print(f"找到JSON數據: {json_data}")
                        except:
                            pass
            
            # 檢查API調用
            print("\n=== 檢查可能的API端點 ===")
            
            # 尋找可能的API URL
            api_patterns = [
                r'api[/\w]*search',
                r'search[/\w]*api',
                r'/api/[^"\']*',
                r'ajax[/\w]*search',
                r'search[/\w]*ajax'
            ]
            
            for pattern in api_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                if matches:
                    print(f"找到可能的API端點: {matches}")
            
            # 檢查表單提交
            forms = soup.find_all('form')
            print(f"\n找到 {len(forms)} 個表單")
            for i, form in enumerate(forms):
                action = form.get('action', '')
                method = form.get('method', 'GET')
                if 'search' in action.lower() or form.find('input', {'name': re.compile('search|q|query', re.I)}):
                    print(f"搜尋表單 {i}: action='{action}', method='{method}'")
            
            # 輸出部分HTML用於分析
            print("\n=== HTML結構樣本 ===")
            print(html_content[:1000])
            print("...")
            print(html_content[-500:])
            
        else:
            print(f"無法訪問網站，狀態碼: {response.status_code}")
            
    except Exception as e:
        print(f"分析過程中發生錯誤: {e}")

if __name__ == "__main__":
    analyze_sapphire_site() 