#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

async def debug_sapphire_html():
    """調試藍寶石網站HTML結構"""
    
    base_url = "https://sapphiretech.cyberbiz.co"
    search_url = f"{base_url}/search?q={quote_plus('9070')}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    print(f"正在訪問: {search_url}")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(search_url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status != 200:
                print(f"HTTP狀態碼錯誤: {response.status}")
                return
            
            html_content = await response.text()
            print(f"HTML內容長度: {len(html_content)}")
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 檢查搜尋結果容器
            search_result = soup.find('div', id='search-result')
            if search_result:
                print("✅ 找到 search-result 容器")
                print(f"search-result 內容長度: {len(search_result.get_text())}")
                
                # 檢查是否為空或只有JavaScript
                text_content = search_result.get_text(strip=True)
                if not text_content:
                    print("❌ search-result 容器為空")
                else:
                    print(f"search-result 文本內容前500字符: {text_content[:500]}")
                
                # 檢查所有子元素
                all_children = search_result.find_all()
                print(f"search-result 包含 {len(all_children)} 個子元素")
                
                # 檢查是否有特定的產品相關元素
                product_indicators = ['product', 'item', 'card', 'grid', 'result']
                for indicator in product_indicators:
                    elements = search_result.find_all(class_=lambda x: x and indicator in x.lower())
                    if elements:
                        print(f"找到 {len(elements)} 個包含 '{indicator}' 的元素")
                        
                        # 顯示第一個元素的結構
                        if elements:
                            first_element = elements[0]
                            print(f"第一個 '{indicator}' 元素:")
                            print(first_element.prettify()[:500])
                            print("...")
                
                # 檢查是否有圖片或鏈接
                images = search_result.find_all('img')
                links = search_result.find_all('a')
                print(f"找到 {len(images)} 個圖片, {len(links)} 個鏈接")
                
                if links:
                    print("前3個鏈接:")
                    for i, link in enumerate(links[:3]):
                        href = link.get('href', '')
                        text = link.get_text(strip=True)
                        print(f"  {i+1}. {text} -> {href}")
                
            else:
                print("❌ 未找到 search-result 容器")
                
                # 檢查其他可能的容器
                possible_containers = [
                    {'tag': 'div', 'class': 'search'},
                    {'tag': 'div', 'class': 'results'},
                    {'tag': 'div', 'class': 'products'},
                    {'tag': 'main'},
                    {'tag': 'section'}
                ]
                
                for container_def in possible_containers:
                    if 'class' in container_def:
                        elements = soup.find_all(container_def['tag'], class_=lambda x: x and container_def['class'] in x.lower())
                    else:
                        elements = soup.find_all(container_def['tag'])
                    
                    if elements:
                        print(f"找到 {len(elements)} 個 {container_def} 元素")
            
            # 檢查JavaScript中是否有產品數據
            scripts = soup.find_all('script')
            print(f"\n檢查 {len(scripts)} 個script標籤...")
            
            for i, script in enumerate(scripts):
                if script.string and ('product' in script.string.lower() or 'search' in script.string.lower()):
                    script_content = script.string
                    if any(keyword in script_content for keyword in ['9070', 'RX', 'SAPPHIRE', 'PULSE']):
                        print(f"Script {i} 可能包含產品數據:")
                        print(script_content[:500])
                        print("...\n")

if __name__ == "__main__":
    asyncio.run(debug_sapphire_html()) 