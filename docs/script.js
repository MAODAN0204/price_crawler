// API 調用和前端交互邏輯
class PriceComparison {
    constructor() {
        this.apiUrl = 'http://localhost:8000';
        this.products = [];
        this.init();
    }

    init() {
        // 綁定事件
        document.getElementById('searchForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.searchProducts();
        });

        document.getElementById('sortBy').addEventListener('change', () => {
            this.sortProducts();
        });

        document.getElementById('apiUrl').addEventListener('change', (e) => {
            this.apiUrl = e.target.value || 'http://localhost:8000';
        });

        // 檢查API狀態
        this.checkApiStatus();
    }

    async checkApiStatus() {
        try {
            const response = await fetch(`${this.apiUrl}/health`);
            if (response.ok) {
                this.showNotification('API 服務正常運行', 'success');
            }
        } catch (error) {
            this.showNotification('無法連接到API服務，請確認後端是否啟動', 'warning');
        }
    }

    async searchProducts() {
        const productName = document.getElementById('productName').value.trim();
        if (!productName) {
            this.showNotification('請輸入產品名稱', 'warning');
            return;
        }

        // 顯示載入狀態
        this.showLoading();

        try {
            // 構建查詢參數
            const params = new URLSearchParams({
                product: productName,
                standalone_only: document.getElementById('standaloneOnly').checked,
                in_stock_only: document.getElementById('inStockOnly').checked
            });

            const minPrice = document.getElementById('minPrice').value;
            const maxPrice = document.getElementById('maxPrice').value;
            
            if (minPrice) params.append('min_price', minPrice);
            if (maxPrice) params.append('max_price', maxPrice);

            const response = await fetch(`${this.apiUrl}/api/search?${params}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.success) {
                this.products = data.data.results || [];
                this.displayResults(data);
                this.updateStats(data.data);
                this.showNotification(data.message, 'success');
            } else {
                throw new Error(data.message || '搜尋失敗');
            }
        } catch (error) {
            console.error('搜尋錯誤:', error);
            this.showNotification(`搜尋失敗: ${error.message}`, 'error');
            this.hideLoading();
        }
    }

    showLoading() {
        document.getElementById('loading').style.display = 'block';
        document.getElementById('results').style.display = 'none';
        document.getElementById('statsSection').style.display = 'none';
    }

    hideLoading() {
        document.getElementById('loading').style.display = 'none';
    }

    updateStats(data) {
        const totalProducts = data.total_found || 0;
        const successStores = data.successful_stores ? data.successful_stores.length : 0;
        
        // 計算平均價格
        const validPrices = this.products.filter(p => p.price > 0).map(p => p.price);
        const avgPrice = validPrices.length > 0 
            ? Math.round(validPrices.reduce((a, b) => a + b, 0) / validPrices.length)
            : 0;

        // 過濾率
        const filterStats = data.filter_stats;
        const filterRate = filterStats ? filterStats.filter_rate : '0%';

        document.getElementById('totalProducts').textContent = totalProducts;
        document.getElementById('successStores').textContent = successStores;
        document.getElementById('avgPrice').textContent = `NT$${avgPrice.toLocaleString()}`;
        document.getElementById('filterRate').textContent = filterRate;
        
        document.getElementById('statsSection').style.display = 'flex';
    }

    displayResults(data) {
        this.hideLoading();
        
        const resultsDiv = document.getElementById('results');
        const productListDiv = document.getElementById('productList');
        
        if (!this.products || this.products.length === 0) {
            productListDiv.innerHTML = `
                <div class="text-center py-5">
                    <i class="fas fa-search fa-3x text-muted mb-3"></i>
                    <h5>未找到相關產品</h5>
                    <p class="text-muted">請嘗試更換關鍵字或調整篩選條件</p>
                </div>
            `;
        } else {
            productListDiv.innerHTML = this.products.map(product => this.createProductCard(product)).join('');
        }
        
        resultsDiv.style.display = 'block';
    }

    createProductCard(product) {
        const stockStatus = product.in_stock 
            ? '<span class="stock-status in-stock"><i class="fas fa-check-circle me-1"></i>有庫存</span>'
            : '<span class="stock-status out-of-stock"><i class="fas fa-times-circle me-1"></i>缺貨</span>';
        
        const bundleTag = product.is_bundle 
            ? '<span class="badge bg-warning text-dark me-2"><i class="fas fa-box me-1"></i>組合包</span>'
            : '';

        const imageHtml = product.image_url 
            ? `<img src="${product.image_url}" alt="${product.product_name}" class="img-thumbnail me-3" style="width: 80px; height: 80px; object-fit: cover;">`
            : '<div class="bg-light rounded me-3 d-flex align-items-center justify-content-center" style="width: 80px; height: 80px;"><i class="fas fa-image text-muted"></i></div>';

        return `
            <div class="product-card">
                <div class="row align-items-center">
                    <div class="col-md-1">
                        ${imageHtml}
                    </div>
                    <div class="col-md-6">
                        <div class="d-flex align-items-center mb-2">
                            <span class="store-badge me-2">${product.store}</span>
                            ${bundleTag}
                            ${stockStatus}
                        </div>
                        <h6 class="mb-1">${this.highlightSearchTerm(product.product_name)}</h6>
                        ${product.specifications ? `<small class="text-muted">${product.specifications}</small>` : ''}
                    </div>
                    <div class="col-md-3 text-center">
                        <div class="price-tag">NT$${product.price.toLocaleString()}</div>
                    </div>
                    <div class="col-md-2 text-end">
                        <a href="${product.url}" target="_blank" class="btn btn-outline-primary btn-sm">
                            <i class="fas fa-external-link-alt me-1"></i>查看詳情
                        </a>
                    </div>
                </div>
            </div>
        `;
    }

    highlightSearchTerm(text) {
        const searchTerm = document.getElementById('productName').value.trim();
        if (!searchTerm) return text;
        
        const regex = new RegExp(`(${searchTerm})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    }

    sortProducts() {
        const sortBy = document.getElementById('sortBy').value;
        
        this.products.sort((a, b) => {
            switch (sortBy) {
                case 'price':
                    return a.price - b.price;
                case 'name':
                    return a.product_name.localeCompare(b.product_name);
                case 'store':
                    return a.store.localeCompare(b.store);
                default:
                    return 0;
            }
        });
        
        this.displayResults({ data: { results: this.products } });
    }

    showNotification(message, type = 'info') {
        // 移除現有通知
        const existingNotification = document.querySelector('.notification');
        if (existingNotification) {
            existingNotification.remove();
        }

        // 創建新通知
        const notification = document.createElement('div');
        notification.className = `notification alert alert-${this.getBootstrapClass(type)} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
        
        notification.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas ${this.getNotificationIcon(type)} me-2"></i>
                <span>${message}</span>
            </div>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // 自動移除通知
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    getBootstrapClass(type) {
        const classMap = {
            'success': 'success',
            'error': 'danger',
            'warning': 'warning',
            'info': 'info'
        };
        return classMap[type] || 'info';
    }

    getNotificationIcon(type) {
        const iconMap = {
            'success': 'fa-check-circle',
            'error': 'fa-exclamation-circle',
            'warning': 'fa-exclamation-triangle',
            'info': 'fa-info-circle'
        };
        return iconMap[type] || 'fa-info-circle';
    }
}

// 初始化應用程式
document.addEventListener('DOMContentLoaded', () => {
    new PriceComparison();
    
    // 添加一些示例搜尋按鈕
    addExampleButtons();
});

function addExampleButtons() {
    const examples = [
        { name: 'RTX 4090', icon: 'fas fa-microchip' },
        { name: 'i9-14900K', icon: 'fas fa-memory' },
        { name: '32GB DDR5', icon: 'fas fa-sd-card' },
        { name: 'RX 9070 XT', icon: 'fas fa-microchip' }
    ];
    
    const exampleContainer = document.createElement('div');
    exampleContainer.className = 'mt-3';
    exampleContainer.innerHTML = `
        <small class="text-muted mb-2 d-block">快速搜尋範例:</small>
        <div class="d-flex flex-wrap gap-2">
            ${examples.map(example => `
                <button type="button" class="btn btn-outline-secondary btn-sm" onclick="setSearchExample('${example.name}')">
                    <i class="${example.icon} me-1"></i>${example.name}
                </button>
            `).join('')}
        </div>
    `;
    
    document.getElementById('productName').parentNode.appendChild(exampleContainer);
}

function setSearchExample(productName) {
    document.getElementById('productName').value = productName;
    document.getElementById('productName').focus();
}

function openGitHub() {
    // 嘗試檢測 GitHub 倉庫 URL
    const repoUrl = 'https://github.com/user/price_crawler'; // 替換為實際的倉庫 URL
    window.open(repoUrl, '_blank');
} 