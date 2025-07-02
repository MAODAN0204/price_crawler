# 電腦產品比價系統

即時爬取台灣電腦產品價格的比價系統，支援多個主流電腦賣場，提供智能產品匹配與組合商品過濾功能。

## ✨ 功能特色

- 🚀 **即時爬取**: 實時獲取最新價格資訊
- 🔄 **並行處理**: 同時爬取多個網站，提升效率
- 💾 **智能快取**: 30分鐘快取機制，避免重複請求
- 🎯 **智能匹配**: 產品名稱相似度匹配與關聯性過濾
- 📊 **價格分析**: 提供價格統計和趨勢分析
- 📱 **響應式介面**: 支援桌面和行動裝置
- 🔍 **組合商品過濾**: 智能識別並過濾組合包、套裝商品
- 🏪 **多店比價**: 一次搜尋多個賣場，快速比較價格
- ⚡ **高效能**: 異步處理，支援大量並行請求

## 🏪 支援的賣場

| 賣場 | 狀態 | 特色功能 |
|------|------|----------|
| ✅ **原價屋 (CoolPC)** | 正常運行 | 完整產品資訊、價格精確 |
| ✅ **德源電腦 (DTSource)** | 正常運行 | 庫存狀態檢測 |
| ✅ **AUTOBUY** | 正常運行 | 組合商品智能過濾 |
| ✅ **欣亞數位 (Sinya)** | 正常運行 | 詳細庫存查詢、組合商品檢測 |
| ✅ **藍寶石官網 (Sapphire)** | 正常運行 | 官方價格、產品規格 |
| ✅ **順發電腦 (Sunfar)** | 正常運行 | 分店庫存資訊 |
| ✅ **PChome 24h** | 正常運行 | 組合包過濾、快速配送 |
| ❌ **momo購物網** | 暫時停用 | 反機器人檢測 |
| ❌ **良興電子 (GH3C)** | 暫時停用 | Cloudflare保護 |
| ❌ **三井3C** | 暫時停用 | 網站結構變更 |

## 🔍 組合商品過濾功能

### 智能檢測機制
系統能自動識別並過濾各種組合商品，確保搜尋結果的精確性：

**檢測的組合商品類型:**
- 🎁 **套裝組合**: 套裝、組合包、套組、大組包
- 💰 **特惠組合**: 超值組、優惠組、特惠組、限量組
- 🏆 **等級組合**: 經濟組、標準組、進階組、旗艦組
- 🛠️ **功能組合**: 基本組、完整組、全配組、專業組
- 🔗 **搭配組合**: 搭機價、合購價、組裝價、救贖包
- 💻 **整機組合**: 電競機、桌機、筆電、工作站

### 使用方式
```bash
# 包含所有商品（含組合包）
GET /api/search?product=RTX4090&standalone_only=false

# 僅顯示單品（過濾組合包）
GET /api/search?product=RTX4090&standalone_only=true
```

## 🛠️ 技術架構

### 後端技術棧
- **FastAPI**: 高效能RESTful API框架
- **aiohttp**: 異步HTTP客戶端，支援並行爬取
- **BeautifulSoup**: 強大的HTML解析器
- **Pydantic**: 型別安全的資料驗證
- **Python 3.11+**: 現代Python特性支援

### 前端技術棧
- **Streamlit**: 簡潔的網頁介面框架
- **Pandas**: 資料處理與分析
- **Requests**: HTTP請求處理

### 核心功能模組
- **產品匹配器**: 智能相似度計算與過濾
- **快取管理**: 高效能記憶體快取
- **價格格式化**: 統一的價格顯示格式
- **組合商品檢測**: 多層級關鍵字匹配

## 📦 安裝說明

### 系統需求
- Python 3.11+
- Windows/macOS/Linux
- 4GB+ RAM（推薦）

### 1. 複製專案
```bash
git clone <repository-url>
cd price_crawler
```

### 2. 安裝相依套件
```bash
pip install -r requirements.txt
```

### 3. 環境設定（可選）
創建 `.env` 檔案：
```env
API_HOST=0.0.0.0
API_PORT=8000
CACHE_EXPIRE_MINUTES=30
REQUEST_DELAY=2
MAX_RETRIES=3
```

## 🚀 使用方法

### 方式一：完整系統（推薦）

1. **啟動後端API**
```bash
cd price_crawler
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

2. **啟動前端介面**（新開終端）
```bash
cd price_crawler
streamlit run app/streamlit_app.py
```

3. **開啟瀏覽器**
- 前端介面：`http://localhost:8501`
- API文檔：`http://localhost:8000/docs`

### 方式二：僅使用API

啟動API後，可直接呼叫：
```bash
# 搜尋RTX 4090（包含組合商品）
curl "http://localhost:8000/api/search?product=RTX%204090&standalone_only=false"

# 搜尋RTX 4090（僅單品）
curl "http://localhost:8000/api/search?product=RTX%204090&standalone_only=true"
```

### 方式三：快速啟動
```bash
# 使用內建腳本
python run.py
```

### 方式四：靜態網頁版本（GitHub Pages）
如果您想部署靜態網頁版本到 GitHub Pages：

1. **推送代碼到 GitHub**：
```bash
git add .
git commit -m "Add GitHub Pages support"
git push origin main
```

2. **啟用 GitHub Pages**：
   - 進入 GitHub 倉庫設定頁面
   - 找到 "Pages" 選項
   - Source 選擇 "GitHub Actions"
   - 系統會自動部署靜態網站

3. **訪問網站**：
```
https://your-username.github.io/price_crawler/
```

**注意**: 靜態版本需要後端 API 服務運行在本地或遠端伺服器上。

## 📖 API 文件

### 🔍 搜尋產品
```
GET /api/search
```

**參數:**
- `product` (必需): 產品名稱或型號
- `standalone_only` (可選): 是否僅顯示單品 (預設: false)
- `sort_by` (可選): 排序方式 (price/name/store)
- `order` (可選): 排序順序 (asc/desc)
- `in_stock_only` (可選): 只顯示有庫存商品
- `min_price` (可選): 最低價格過濾
- `max_price` (可選): 最高價格過濾

**回應範例:**
```json
{
  "success": true,
  "message": "找到 26 個相關產品",
  "data": {
    "product": "RTX 4090",
    "timestamp": "2025-01-02T16:45:56.429879",
    "results": [
      {
        "store": "原價屋",
        "product_name": "ASUS RTX 4090 TUF Gaming OC 24GB",
        "price": 45000.0,
        "url": "https://coolpc.com.tw/...",
        "in_stock": true,
        "image_url": "https://...",
        "specifications": "24GB GDDR6X",
        "is_bundle": false
      }
    ],
    "total_found": 26,
    "successful_stores": ["原價屋", "德源電腦", "AUTOBUY", "欣亞數位"],
    "failed_stores": [],
    "filter_stats": {
      "total_before_filter": 90,
      "total_after_filter": 26,
      "filtered_count": 64,
      "filter_rate": "71.1%"
    }
  }
}
```

### 🔗 其他端點
- `GET /` - API 資訊與系統狀態
- `GET /health` - 健康檢查
- `GET /api/cache/stats` - 快取統計資訊
- `DELETE /api/cache` - 清空快取

### 🏪 個別賣場端點
- `GET /api/pchome/search` - PChome 24h 專用搜尋

## 📁 專案結構

```
price_crawler/
├── app/
│   ├── main.py                  # FastAPI 主應用
│   ├── streamlit_app.py         # Streamlit 前端介面
│   ├── config.py                # 設定檔
│   ├── scrapers/                # 爬蟲模組
│   │   ├── __init__.py
│   │   ├── base_scraper.py      # 基礎爬蟲類別
│   │   ├── coolpc.py            # 原價屋爬蟲
│   │   ├── dtsource.py          # 德源電腦爬蟲
│   │   ├── autobuy.py           # AUTOBUY爬蟲
│   │   ├── sinya.py             # 欣亞數位爬蟲
│   │   ├── sapphire.py          # 藍寶石官網爬蟲
│   │   ├── sunfar.py            # 順發電腦爬蟲
│   │   └── pchome.py            # PChome 24h爬蟲
│   ├── models/                  # 資料模型
│   │   ├── __init__.py
│   │   └── product.py           # 產品模型（支援組合商品標記）
│   └── utils/                   # 工具函數
│       ├── __init__.py
│       ├── cache.py             # 快取管理
│       ├── product_matcher.py   # 智能產品匹配
│       └── price_formatter.py   # 價格格式化
├── requirements.txt             # Python 套件清單
├── run.py                      # 快速啟動腳本
└── README.md                   # 說明文件
```

## 💡 使用範例

### 🎮 搜尋顯示卡
```bash
# 最新顯示卡
"RTX 5090"    # NVIDIA最新旗艦卡
"RTX 5080"    # NVIDIA次旗艦卡
"RX 9070 XT"  # AMD最新高階卡

# 主流顯示卡
"RTX 4090"    # NVIDIA上代旗艦
"RTX 4080"    # NVIDIA上代次旗艦
"RTX 4070"    # 主流高階選擇
```

### 🖥️ 搜尋處理器
```bash
# Intel處理器
"i9-14900K"   # Intel旗艦處理器
"i7-14700K"   # 主流高階選擇
"i5-14600K"   # 性價比之選

# AMD處理器
"Ryzen 9 9950X"  # AMD旗艦處理器
"Ryzen 7 9700X"  # 主流高階選擇
"Ryzen 5 9600X"  # 性價比之選
```

### 💾 搜尋記憶體
```bash
"32GB DDR5"      # 高容量DDR5
"16GB DDR4 3200" # 主流DDR4
"64GB DDR5 6000" # 極高容量高頻
```

## ⚠️ 注意事項

### 使用規範
1. **合理使用**: 請避免過度頻繁請求，建議間隔2秒以上
2. **尊重網站**: 遵守各網站的使用條款和robots.txt
3. **資料準確性**: 價格僅供參考，實際價格以各賣場官網為準
4. **庫存狀態**: 庫存資訊可能有延遲，建議購買前再次確認

### 效能考量
- 首次搜尋較慢（需爬取多個網站）
- 後續搜尋利用快取機制大幅提升速度
- 建議使用具體產品型號提高匹配精確度

## 🛠️ 開發指南

### 新增爬蟲步驟

1. **建立爬蟲檔案**
```python
# app/scrapers/your_store.py
from .base_scraper import BaseScraper
from ..models.product import Product

class YourStoreScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            store_name="您的商店",
            base_url="https://yourstore.com"
        )
    
    async def search_products(self, product_name: str, standalone_only: bool = False) -> List[Product]:
        # 實作搜尋邏輯
        pass
```

2. **註冊爬蟲**
在 `app/main.py` 的 `SCRAPERS` 字典中新增：
```python
SCRAPERS = {
    # ... 其他爬蟲
    "yourstore": YourStoreScraper(),
}
```

### 測試新爬蟲
```python
import asyncio
from app.scrapers.your_store import YourStoreScraper

async def test_scraper():
    scraper = YourStoreScraper()
    products = await scraper.search_products("RTX 4090")
    print(f"找到 {len(products)} 個產品")
    
    # 測試組合商品過濾
    standalone_products = await scraper.search_products("RTX 4090", standalone_only=True)
    print(f"單品數量: {len(standalone_products)}")

asyncio.run(test_scraper())
```

## 🐛 故障排除

### 常見問題與解決方案

#### 1. API 連接失敗
**問題**: 無法連接到後端API
**解決方案**:
```bash
# 檢查服務狀態
netstat -an | findstr 8000

# 重新啟動API服務
python -m uvicorn app.main:app --reload
```

#### 2. 爬取失敗
**問題**: 某些網站無法爬取
**可能原因**:
- 網站結構變更
- 反爬機制啟動
- 網路連接問題

**解決方案**:
- 檢查錯誤日誌
- 確認網站可正常訪問
- 更新爬蟲邏輯

#### 3. 搜尋結果不準確
**問題**: 搜尋到不相關的產品
**解決方案**:
- 使用更具體的關鍵字
- 包含品牌名稱和完整型號
- 啟用組合商品過濾 (`standalone_only=true`)

### 日誌分析
API 日誌會即時顯示：
- 🔍 搜尋請求詳情
- ⚡ 各賣場爬取狀態
- ❌ 錯誤訊息與堆疊
- 📊 效能與統計資訊

## 🔄 更新日誌

### v2.0.0 (2025-01-02) - 最新版本
- ✅ **新增7個賣場**: AUTOBUY、欣亞數位、藍寶石、順發、PChome等
- ✅ **組合商品過濾**: 智能識別並過濾各種組合包商品
- ✅ **產品模型升級**: 新增 `is_bundle` 欄位標記組合商品
- ✅ **改善使用者介面**: 更新為「搜尋商品型號」提升用戶體驗
- ✅ **錯誤處理優化**: 更完善的異常處理與錯誤訊息
- ✅ **效能提升**: 優化爬取邏輯，提升回應速度

### v1.5.0 (2024-12-15)
- ✅ **原價屋爬蟲修復**: 解決JavaScript渲染問題，支援最新產品
- ✅ **快取機制優化**: 提升快取效率，減少重複請求
- ✅ **產品匹配改進**: 更精確的相似度計算演算法

### v1.0.0 (2024-01-01)
- ✅ **基礎架構建立**: FastAPI + Streamlit 架構
- ✅ **原價屋爬蟲**: 第一個爬蟲實作
- ✅ **德源電腦爬蟲**: 第二個賣場支援
- ✅ **產品匹配邏輯**: 基礎相似度匹配

## 📄 授權條款

本專案採用 MIT 授權條款，僅供學習和個人使用。

**重要聲明**:
- 🚫 請勿用於商業用途
- 🚫 請勿進行大量自動化請求
- ✅ 使用時請遵守各網站的使用條款
- ✅ 尊重網站的反爬機制

## 🤝 貢獻指南

歡迎提交 Issue 和 Pull Request 來改善本專案！

### 如何貢獻
1. **Fork** 本專案到您的帳號
2. **建立功能分支** (`git checkout -b feature/AmazingFeature`)
3. **提交變更** (`git commit -m 'Add some AmazingFeature'`)
4. **推送分支** (`git push origin feature/AmazingFeature`)
5. **開啟 Pull Request**

### 開發規範
- 遵循現有的程式碼風格
- 為新功能撰寫測試
- 更新相關文檔
- 確保不破壞現有功能

### 問題回報
提交Issue時請包含：
- 詳細的問題描述
- 重現步驟
- 預期行為
- 實際行為
- 系統環境資訊

---

🌟 **如果這個專案對您有幫助，請給個星星支持！** ⭐

📧 **問題與建議**: 歡迎透過GitHub Issues與我們聯絡 