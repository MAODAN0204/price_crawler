# 電腦產品比價系統 - 使用示範

## 🚀 快速開始

### 方法一：使用啟動腳本（推薦）

```bash
# 在專案根目錄執行
python run.py
```

選擇選項：
1. **完整系統** - 同時啟動API和網頁介面
2. **僅啟動API** - 只啟動後端服務
3. **僅啟動網頁介面** - 只啟動前端（需要API已在運行）
4. **測試模式** - 執行系統測試

### 方法二：手動啟動

```bash
# 終端1：啟動API
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 終端2：啟動前端
streamlit run app/streamlit_app.py
```

## 📱 訪問介面

- **網頁介面**: http://localhost:8501
- **API文件**: http://localhost:8000/docs
- **API根路徑**: http://localhost:8000

## 💡 使用示範

### 1. 網頁介面使用

1. 打開 http://localhost:8501
2. 在搜尋框輸入產品名稱，例如：
   - `RTX 4090`
   - `i9-13900K`
   - `32GB DDR5`
   - `1TB SSD`
3. 調整側邊欄的篩選選項：
   - 排序方式（價格/名稱/店家）
   - 排序順序（由低到高/由高到低）
   - 只顯示有庫存商品
   - 價格範圍篩選
4. 點擊「開始比價」
5. 查看結果並可下載CSV

### 2. API直接使用

```bash
# 基本搜尋
curl "http://localhost:8000/api/search?product=RTX%204090"

# 帶參數的搜尋
curl "http://localhost:8000/api/search?product=RTX%204090&sort_by=price&order=asc&in_stock_only=true"

# 健康檢查
curl "http://localhost:8000/health"

# 快取統計
curl "http://localhost:8000/api/cache/stats"
```

### 3. Python程式使用

```python
import requests
import json

# 搜尋產品
response = requests.get("http://localhost:8000/api/search", params={
    "product": "RTX 4090",
    "sort_by": "price",
    "order": "asc"
})

data = response.json()
if data["success"]:
    print(f"找到 {data['data']['total_found']} 個產品")
    for product in data["data"]["results"]:
        print(f"{product['store']}: {product['product_name']} - NT$ {product['price']}")
```

## 🔍 搜尋技巧

### 顯示卡搜尋
- `RTX 4090` - NVIDIA RTX 4090
- `RTX 4080 SUPER` - 新款RTX 4080 SUPER
- `RTX 4070 Ti` - 中階顯卡
- `RX 7900 XTX` - AMD旗艦顯卡

### 處理器搜尋
- `i9-13900K` - Intel第13代旗艦
- `i7-13700K` - Intel第13代高階
- `i5-13600K` - Intel第13代中階
- `Ryzen 9 7950X` - AMD旗艦處理器

### 記憶體搜尋
- `32GB DDR5` - 32GB DDR5記憶體
- `16GB DDR4 3200` - 16GB DDR4 3200MHz
- `64GB DDR5 5600` - 高階記憶體

### 儲存裝置搜尋
- `1TB SSD` - 1TB固態硬碟
- `2TB NVMe` - 2TB NVMe SSD
- `4TB HDD` - 4TB傳統硬碟

## 📊 功能特色

### 智能匹配
- 自動識別不同店家的產品命名差異
- 品牌、型號、規格智能匹配
- 相似度評分排序

### 並行爬取
- 同時爬取多個網站
- 異步處理提升效率
- 錯誤重試機制

### 智能快取
- 30分鐘內快取結果
- 避免重複請求
- 記憶體管理優化

### 資料分析
- 價格統計（最低/最高/平均）
- 庫存狀態分析
- 店家成功率統計

## 🔧 自訂設定

### 環境變數設定（可選）

創建 `.env` 檔案：
```env
API_HOST=0.0.0.0
API_PORT=8000
CACHE_EXPIRE_MINUTES=30
REQUEST_DELAY=2
MAX_RETRIES=3
TIMEOUT_SECONDS=30
HEADLESS_MODE=true
```

### 修改目標網站

編輯 `app/config.py`：
```python
TARGET_STORES = [
    "coolpc",      # 原價屋
    "dtsource",    # 德源電腦
    # 可添加更多網站
]
```

## 🐛 故障排除

### 常見問題

1. **模組導入錯誤**
   ```bash
   pip install -r requirements.txt
   ```

2. **端口被佔用**
   ```bash
   # 更改端口
   python -m uvicorn app.main:app --port 8001
   streamlit run app/streamlit_app.py --server.port 8502
   ```

3. **爬取失敗**
   - 檢查網路連接
   - 確認目標網站可訪問
   - 查看終端錯誤訊息

4. **搜尋結果太少**
   - 使用更通用的關鍵字
   - 降低相似度門檻
   - 檢查網站是否有反爬機制

### 除錯模式

```bash
# 啟用詳細日誌
python -m uvicorn app.main:app --log-level debug

# 測試單一爬蟲
python -c "
import asyncio
from app.scrapers.coolpc import CoolPCScraper

async def test():
    async with CoolPCScraper() as scraper:
        products = await scraper.search_products('RTX 4090')
        print(f'找到 {len(products)} 個產品')

asyncio.run(test())
"
```

## 📈 性能優化

### 爬取優化
- 調整 `REQUEST_DELAY` 平衡速度和穩定性
- 增加 `MAX_RETRIES` 提升成功率
- 使用合適的 `TIMEOUT_SECONDS`

### 快取優化
- 調整 `CACHE_EXPIRE_MINUTES` 平衡即時性和效率
- 監控 `MAX_CACHE_SIZE` 避免記憶體不足

### 網路優化
- 使用穩定的網路連接
- 考慮使用代理伺服器（進階功能）

## 🛡️ 注意事項

1. **遵守網站條款**：請遵守各網站的使用條款和robots.txt
2. **合理使用**：避免過度頻繁的請求
3. **資料準確性**：價格僅供參考，實際價格以各網站為準
4. **隱私保護**：不收集個人資訊，僅爬取公開商品資訊

## 📞 支援

如遇問題或有建議，請：
1. 檢查這份文件的故障排除章節
2. 查看終端的錯誤訊息
3. 確認系統需求和依賴項
4. 嘗試重新安裝依賴項 