import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time
import io

# 頁面配置
st.set_page_config(
    page_title="電腦產品比價系統",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 全局變數
API_BASE_URL = "http://127.0.0.1:8000"

def main():
    """主要應用程式"""
    
    # 初始化 session state
    if 'search_results' not in st.session_state:
        st.session_state.search_results = None
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    if 'per_page' not in st.session_state:
        st.session_state.per_page = 10
    if 'last_search_query' not in st.session_state:
        st.session_state.last_search_query = ""
    
    # 標題和描述
    st.title("💻 電腦產品比價系統")
    st.markdown("即時比較台灣各大電腦賣場的產品價格")
    
    # 側邊欄
    with st.sidebar:
        st.header("🔧 搜尋設定")
        
        # 搜尋選項
        sort_by = st.selectbox(
            "排序方式",
            options=["price", "name", "store"],
            format_func=lambda x: {"price": "價格", "name": "產品名稱", "store": "店家"}[x],
            index=0
        )
        
        order = st.selectbox(
            "排序順序",
            options=["asc", "desc"],
            format_func=lambda x: {"asc": "由低到高", "desc": "由高到低"}[x],
            index=0
        )
        
        in_stock_only = st.checkbox("只顯示有庫存商品", value=False)
        standalone_only = st.checkbox("只顯示單獨商品", value=False, 
                                    help="排除整機電腦、筆電等組合產品，只顯示單獨零件")
        
        # 顯示設定
        st.subheader("📄 顯示設定")
        per_page = st.selectbox(
            "每頁顯示數量",
            options=[10, 20, 50, 100, "全部"],
            index=0,
            help="選擇每頁要顯示的商品數量"
        )
        
        # 當每頁顯示數量改變時，重置到第一頁
        if per_page != st.session_state.per_page:
            st.session_state.per_page = per_page
            st.session_state.current_page = 1
        
        # 價格篩選
        st.subheader("💰 價格篩選")
        price_range = st.slider(
            "價格範圍 (NT$)",
            min_value=0,
            max_value=100000,
            value=(0, 100000),
            step=1000
        )
        
        min_price = price_range[0] if price_range[0] > 0 else None
        max_price = price_range[1] if price_range[1] < 100000 else None
        
        # 快取控制
        st.subheader("🗄️ 快取控制")
        if st.button("清空快取"):
            clear_cache()
        
        if st.button("檢視快取統計"):
            show_cache_stats()
    
    # 主要內容區域
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # 搜尋框
        product_query = st.text_input(
            "🔍 輸入產品名稱",
            placeholder="例如：RTX 4090、i9-13900K、32GB DDR5",
            help="輸入您要搜尋的電腦產品名稱或型號"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # 空間調整
        search_button = st.button("🚀 開始比價", type="primary", use_container_width=True)
    
    # 搜尋結果區域
    if search_button and product_query:
        # 重置頁碼當新搜尋時
        if product_query != st.session_state.last_search_query:
            st.session_state.current_page = 1
            st.session_state.last_search_query = product_query
        
        search_results = search_products(
            product_query, 
            sort_by, 
            order, 
            in_stock_only,
            standalone_only,
            min_price, 
            max_price
        )
        
        if search_results:
            st.session_state.search_results = search_results
    
    # 顯示搜尋結果（如果有的話）
    if st.session_state.search_results:
        display_search_results(st.session_state.search_results, st.session_state.per_page)
    
    # 說明區域
    with st.expander("📖 使用說明"):
        st.markdown("""
        ### 如何使用
        1. 在搜尋框中輸入產品名稱或型號
        2. 調整側邊欄的篩選和排序選項
        3. 點選「開始比價」按鈕
        4. 等待系統搜尋各大賣場的商品價格
        5. 查看比價結果並點擊連結前往購買
        
        ### 支援的賣場
        - 🏪 德源電腦 (支援過濾合購商品)
        - 🏪 AUTOBUY購物中心
        - 🏪 欣亞數位 (支援過濾組合商品)
        - 🏪 藍寶石官網
        - 🏪 順發電腦
        - 🏪 PChome 24h購物 (支援過濾組合包)
        - 🏪 原價屋 (支援過濾專案商品)
        
        ### 搜尋技巧
        - 使用產品型號獲得更精確的結果 (如：RTX 4090)
        - 包含品牌名稱 (如：ASUS RTX 4090)
        - 避免使用過於複雜的描述
        """)
    
    # 頁腳
    st.markdown("---")
    st.markdown(
        "🔧 **電腦產品比價系統** | "
        "即時搜尋價格資訊，僅供參考，實際價格以各賣場為準 | "
        f"更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

def search_products(product_query, sort_by, order, in_stock_only, standalone_only, min_price, max_price):
    """搜尋產品並返回結果"""
    
    # 顯示載入狀態
    with st.spinner("🔍 正在搜尋產品，請稍候..."):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 模擬進度更新
        for i in range(7):
            progress_bar.progress((i + 1) * 14)  # 7 * 14 ≈ 100%
            status_text.text(f"正在搜尋商品型號第 {i + 1}/7 個賣場...")
            time.sleep(0.2)
        
        # 發送API請求
        try:
            params = {
                "product": product_query,
                "sort_by": sort_by,
                "order": order,
                "in_stock_only": in_stock_only,
                "standalone_only": standalone_only
            }
            
            if min_price:
                params["min_price"] = min_price
            if max_price:
                params["max_price"] = max_price
            
            response = requests.get(f"{API_BASE_URL}/api/search", params=params, timeout=60)
            data = response.json()
            
            progress_bar.progress(100)
            status_text.text("搜尋完成！")
            
        except requests.exceptions.ConnectionError:
            st.error("❌ 無法連接到後端API。請確保API服務器正在運行。")
            return None
        except requests.exceptions.Timeout:
            st.error("⏱️ 搜尋超時，請稍後再試。")
            return None
        except Exception as e:
            st.error(f"❌ 搜尋時發生錯誤：{str(e)}")
            return None
    
    # 清除進度顯示
    progress_bar.empty()
    status_text.empty()
    
    # 處理搜尋結果
    if not data.get("success", False):
        st.warning(f"⚠️ {data.get('message', '搜尋失敗')}")
        if data.get("error"):
            st.error(f"錯誤詳情：{data['error']}")
        return None
    
    search_result = data.get("data")
    if not search_result or not search_result.get("results"):
        st.info("📭 未找到相關產品，請嘗試其他關鍵字。")
        return None
    
    return search_result

def display_search_results(search_result, per_page):
    """顯示搜尋結果與分頁"""
    
    # 顯示搜尋摘要
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🎯 找到商品", search_result["total_found"])
    
    with col2:
        st.metric("✅ 成功賣場", len(search_result["successful_stores"]))
    
    with col3:
        st.metric("❌ 失敗賣場", len(search_result["failed_stores"]))
    
    with col4:
        cache_time = datetime.fromisoformat(search_result["timestamp"].replace('Z', '+00:00'))
        st.metric("🕐 搜尋時間", cache_time.strftime("%H:%M:%S"))
    
    # 顯示失敗的賣場
    if search_result["failed_stores"]:
        st.warning(f"⚠️ 以下賣場搜尋失敗：{', '.join(search_result['failed_stores'])}")
    
    # 顯示產品列表
    st.subheader("📊 比價結果")
    
    # 轉換為DataFrame
    products_data = []
    for product in search_result["results"]:
        products_data.append({
            "店家": product["store"],
            "產品名稱": product["product_name"],
            "價格": f"NT$ {product['price']:,.0f}",
            "庫存": "✅ 有庫存" if product["in_stock"] else "❌ 無庫存",
            "連結": product["url"]
        })
    
    if products_data:
        df = pd.DataFrame(products_data)
        
        # 分頁邏輯
        total_items = len(df)
        
        if per_page == "全部":
            # 顯示全部結果
            st.info(f"📋 顯示全部 {total_items} 個結果")
            displayed_df = df
            total_pages = 1
            st.session_state.current_page = 1
        else:
            # 分頁顯示
            per_page_int = int(per_page)
            total_pages = (total_items + per_page_int - 1) // per_page_int
            
            # 確保當前頁碼在有效範圍內
            if st.session_state.current_page > total_pages:
                st.session_state.current_page = total_pages
            if st.session_state.current_page < 1:
                st.session_state.current_page = 1
            
            # 分頁控制
            if total_pages > 1:
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    # 使用selectbox來選擇頁碼，綁定到session_state
                    new_page = st.selectbox(
                        f"📄 頁碼 (共 {total_pages} 頁)",
                        range(1, total_pages + 1),
                        index=st.session_state.current_page - 1,
                        key="page_selector"
                    )
                    if new_page != st.session_state.current_page:
                        st.session_state.current_page = new_page
                        st.rerun()
            
            # 計算顯示範圍
            start_idx = (st.session_state.current_page - 1) * per_page_int
            end_idx = start_idx + per_page_int
            displayed_df = df.iloc[start_idx:end_idx]
            
            # 顯示分頁資訊
            st.info(f"📋 第 {st.session_state.current_page} 頁，共 {total_pages} 頁 (第 {start_idx + 1}-{min(end_idx, total_items)} 項，共 {total_items} 項)")
        
        # 顯示表格
        st.dataframe(
            displayed_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "連結": st.column_config.LinkColumn(
                    "前往購買",
                    help="點擊前往該商品頁面"
                )
            }
        )
        
        # 分頁導航按鈕（如果有多頁）
        if per_page != "全部" and total_pages > 1:
            col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
            
            with col1:
                if st.session_state.current_page > 1:
                    if st.button("⏪ 第一頁"):
                        st.session_state.current_page = 1
                        st.rerun()
            
            with col2:
                if st.session_state.current_page > 1:
                    if st.button("◀️ 上一頁"):
                        st.session_state.current_page -= 1
                        st.rerun()
            
            with col3:
                st.markdown(f"<div style='text-align: center; padding: 8px;'><strong>{st.session_state.current_page} / {total_pages}</strong></div>", unsafe_allow_html=True)
            
            with col4:
                if st.session_state.current_page < total_pages:
                    if st.button("▶️ 下一頁"):
                        st.session_state.current_page += 1
                        st.rerun()
            
            with col5:
                if st.session_state.current_page < total_pages:
                    if st.button("⏩ 最後頁"):
                        st.session_state.current_page = total_pages
                        st.rerun()
        
        # 功能按鈕
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📥 下載當前頁CSV"):
                download_csv(displayed_df, st.session_state.last_search_query, f"第{st.session_state.current_page}頁")
        
        with col2:
            if st.button("📥 下載全部結果CSV"):
                download_csv(df, st.session_state.last_search_query, "全部結果")
        
        # 價格分析
        show_price_analysis(search_result["results"])

def download_csv(df, product_query, filename):
    """下載CSV功能"""
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
    csv_data = csv_buffer.getvalue()
    
    st.download_button(
        label="💾 下載比價結果",
        data=csv_data,
        file_name=f"{product_query}_比價結果_{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

def show_price_analysis(products):
    """顯示價格分析"""
    if len(products) < 2:
        return
    
    prices = [p["price"] for p in products if p["in_stock"]]
    
    if not prices:
        return
    
    st.subheader("📈 價格分析")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💰 最低價", f"NT$ {min(prices):,.0f}")
    
    with col2:
        st.metric("💸 最高價", f"NT$ {max(prices):,.0f}")
    
    with col3:
        st.metric("📊 平均價", f"NT$ {sum(prices)/len(prices):,.0f}")
    
    with col4:
        price_diff = max(prices) - min(prices)
        st.metric("📉 價差", f"NT$ {price_diff:,.0f}")

def clear_cache():
    """清空快取"""
    try:
        response = requests.delete(f"{API_BASE_URL}/api/cache")
        if response.status_code == 200:
            st.success("✅ 快取已清空")
        else:
            st.error("❌ 清空快取失敗")
    except Exception as e:
        st.error(f"❌ 清空快取時發生錯誤：{str(e)}")

def show_cache_stats():
    """顯示快取統計"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/cache/stats")
        if response.status_code == 200:
            stats = response.json()
            st.info(
                f"📊 快取統計：\n"
                f"- 項目數量：{stats['total_items']}\n"
                f"- 最大容量：{stats['max_size']}\n"
                f"- 過期時間：{stats['expire_minutes']} 分鐘"
            )
        else:
            st.error("❌ 無法獲取快取統計")
    except Exception as e:
        st.error(f"❌ 獲取快取統計時發生錯誤：{str(e)}")

if __name__ == "__main__":
    main() 