import re
from typing import List, Dict, Any
from difflib import SequenceMatcher

class ProductMatcher:
    """產品匹配工具類"""
    
    def __init__(self):
        # 常見品牌和型號的同義詞映射
        self.brand_synonyms = {
            'nvidia': ['nvidia', 'geforce', 'gtx', 'rtx'],
            'amd': ['amd', 'radeon', 'ryzen'],
            'intel': ['intel', 'core'],
            'asus': ['asus', '華碩'],
            'msi': ['msi', '微星'],
            'gigabyte': ['gigabyte', '技嘉'],
            'asrock': ['asrock', '華擎'],
            'corsair': ['corsair', '海盜船'],
            'kingston': ['kingston', '金士頓'],
            'western digital': ['wd', 'western digital', '威騰'],
            'seagate': ['seagate', '希捷']
        }
        
        # 常見規格縮寫
        self.spec_patterns = {
            'memory': r'(\d+)GB',
            'storage': r'(\d+)(GB|TB)',
            'frequency': r'(\d+)MHz',
            'cores': r'(\d+)核心?',
            'model_number': r'[A-Z]+\d+[A-Z]*'
        }
    
    def normalize_search_term(self, term: str) -> str:
        """標準化搜尋詞彙"""
        if not term:
            return ""
        
        # 轉為小寫並移除特殊字符
        normalized = re.sub(r'[^\w\s\-]', ' ', term.lower())
        
        # 移除多餘空格
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def extract_key_features(self, product_name: str) -> Dict[str, Any]:
        """提取產品關鍵特徵"""
        features = {
            'brand': None,
            'model': None,
            'memory': None,
            'storage': None,
            'specs': []
        }
        
        normalized_name = self.normalize_search_term(product_name)
        
        # 提取品牌
        for brand, synonyms in self.brand_synonyms.items():
            for synonym in synonyms:
                if synonym in normalized_name:
                    features['brand'] = brand
                    break
            if features['brand']:
                break
        
        # 提取型號和規格
        for spec_type, pattern in self.spec_patterns.items():
            matches = re.findall(pattern, normalized_name, re.IGNORECASE)
            if matches:
                if spec_type in ['memory', 'storage']:
                    features[spec_type] = matches[0] if isinstance(matches[0], str) else matches[0][0]
                features['specs'].extend(matches)
        
        # 提取型號（如RTX 4090, i9-13900K等）
        model_match = re.search(r'(rtx|gtx|rx|i\d|ryzen)\s*\d+[a-z]*', normalized_name, re.IGNORECASE)
        if model_match:
            features['model'] = model_match.group(0).upper().replace(' ', '')
        
        return features
    
    def calculate_similarity(self, search_term: str, product_name: str) -> float:
        """計算搜尋詞與產品名稱的相似度"""
        search_normalized = self.normalize_search_term(search_term)
        product_normalized = self.normalize_search_term(product_name)
        
        # 檢查是否有直接的子字符串匹配 - 這很重要！
        direct_match_score = 0
        if search_normalized in product_normalized:
            # 根據搜尋詞在產品名稱中的相對長度給分
            match_ratio = len(search_normalized) / len(product_normalized)
            direct_match_score = 0.3 + (match_ratio * 0.4)  # 基礎0.3分，最高0.7分
        
        # 使用SequenceMatcher計算基本相似度
        basic_similarity = SequenceMatcher(None, search_normalized, product_normalized).ratio()
        
        # 提取關鍵特徵進行比較
        search_features = self.extract_key_features(search_term)
        product_features = self.extract_key_features(product_name)
        
        # 計算特徵匹配度
        feature_score = 0
        total_features = 0
        
        # 品牌匹配
        if search_features['brand'] and product_features['brand']:
            total_features += 1
            if search_features['brand'] == product_features['brand']:
                feature_score += 1
        
        # 型號匹配 - 這是最重要的匹配，給予更高權重
        if search_features['model'] and product_features['model']:
            total_features += 2  # 型號匹配權重加倍
            if search_features['model'] == product_features['model']:
                feature_score += 2  # 完全匹配給2分
            elif search_features['model'][:3] == product_features['model'][:3]:
                feature_score += 0.5  # 部分匹配給0.5分
        
        # 數字匹配 - 對於純數字搜尋（如5080）特別重要
        search_numbers = re.findall(r'\d+', search_normalized)
        product_numbers = re.findall(r'\d+', product_normalized)
        if search_numbers and product_numbers:
            total_features += 1
            # 檢查搜尋的數字是否出現在產品中
            number_matches = sum(1 for num in search_numbers if num in product_numbers)
            if number_matches > 0:
                feature_score += number_matches / len(search_numbers)
        
        # 規格匹配
        if search_features['specs'] and product_features['specs']:
            total_features += 1
            common_specs = set(search_features['specs']) & set(product_features['specs'])
            if common_specs:
                feature_score += len(common_specs) / max(len(search_features['specs']), len(product_features['specs']))
        
        # 綜合評分
        if total_features > 0:
            feature_similarity = feature_score / total_features
            # 加權平均：直接匹配30%，基本相似度20%，特徵相似度50%
            final_score = direct_match_score * 0.3 + basic_similarity * 0.2 + feature_similarity * 0.5
        else:
            # 如果沒有特徵匹配，但有直接匹配，仍給較高分數
            final_score = max(direct_match_score, basic_similarity)
        
        return min(final_score, 1.0)
    
    def is_relevant_product(self, search_term: str, product_name: str, threshold: float = 0.3) -> bool:
        """判斷產品是否與搜尋詞相關"""
        similarity = self.calculate_similarity(search_term, product_name)
        return similarity >= threshold
    
    def is_standalone_product(self, product_name: str) -> bool:
        """判斷產品是否為單獨商品（非整機/筆電/組合）"""
        product_lower = product_name.lower()
        
        # 整機/組合產品關鍵字
        combo_keywords = [
            # 電腦相關
            '電腦', '主機', '桌機', 'pc', 'desktop', 'nuc', '迷你電腦',
            # 筆電相關
            '筆電', '筆記型電腦', 'laptop', 'notebook',
            # 工作站
            '工作站', 'workstation',
            # 組合套裝
            '套裝', '組合', '套組', '救贖', '升級版', '雙碟版',
            # 品牌整機系列
            'rog strix scar', 'rog strix g', 'tuf gaming a', 'tuf gaming f',
            'predator', 'legion', 'alienware', 'pavilion',
            'stealth', 'creator', 'crosshair', 'katana', 'vector',
            'aorus master', 'aorus elite', 'infinite x', 'aegis',
            'rog nuc', 'intel nuc', 'mini pc',
            # 特殊配置描述
            'ryzen', 'intel', 'i5', 'i7', 'i9', 'ddr', 'ssd', 'hdd',
            '記憶體', '硬碟', '散熱器', '電源', '機殼', 'ultra 9', 'ultra',
            # 作業系統
            'w11', 'windows', 'win10', 'win11',
            # 容量描述（通常整機才會詳細描述）
            '32g', '64g', '1tb', '2tb', '16g/', '32g/', '64g/'
        ]
        
        # 檢查是否包含組合產品關鍵字
        for keyword in combo_keywords:
            if keyword in product_lower:
                return False
        
        # 檢查是否包含多個硬體組件描述（表示是整機）
        hardware_components = [
            'cpu', 'gpu', 'ram', 'ssd', 'hdd', 'psu', 'mb', 'motherboard',
            '處理器', '顯示卡', '記憶體', '硬碟', '電源', '主機板'
        ]
        
        component_count = sum(1 for component in hardware_components if component in product_lower)
        if component_count >= 2:  # 如果包含2個或以上硬體組件，可能是整機
            return False
        
        return True
    
    def filter_relevant_products(self, search_term: str, products: List[Dict[str, Any]], threshold: float = 0.3, standalone_only: bool = False) -> List[Dict[str, Any]]:
        """過濾相關產品"""
        relevant_products = []
        
        for product in products:
            product_name = product.get('product_name', '')
            
            # 相關性檢查
            if not self.is_relevant_product(search_term, product_name, threshold):
                continue
            
            # 單獨商品檢查
            if standalone_only:
                # 優先使用產品模型中的 is_bundle 字段
                if product.get('is_bundle', False):
                    continue
                # 如果沒有 is_bundle 字段，使用舊的檢查方法作為備用
                elif 'is_bundle' not in product and not self.is_standalone_product(product_name):
                    continue
            
            # 添加相似度分數
            product['similarity_score'] = self.calculate_similarity(search_term, product_name)
            relevant_products.append(product)
        
        # 按相似度排序
        relevant_products.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
        
        return relevant_products 