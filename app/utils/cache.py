import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.config import Config

class CacheManager:
    """記憶體快取管理器"""
    
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = Config.MAX_CACHE_SIZE
        self.expire_minutes = Config.CACHE_EXPIRE_MINUTES
    
    def _generate_key(self, product_name: str) -> str:
        """生成快取鍵值"""
        return hashlib.md5(product_name.lower().encode()).hexdigest()
    
    def _is_expired(self, cache_entry: Dict[str, Any]) -> bool:
        """檢查快取是否過期"""
        expire_time = cache_entry.get("expires_at")
        if not expire_time:
            return True
        return datetime.now() > expire_time
    
    def _cleanup_expired(self):
        """清理過期的快取項目"""
        expired_keys = []
        for key, entry in self.cache.items():
            if self._is_expired(entry):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
    
    def _manage_size(self):
        """管理快取大小"""
        if len(self.cache) >= self.max_size:
            # 移除最舊的項目
            oldest_key = min(
                self.cache.keys(), 
                key=lambda k: self.cache[k].get("created_at", datetime.min)
            )
            del self.cache[oldest_key]
    
    def get(self, product_name: str) -> Optional[Dict[str, Any]]:
        """取得快取資料"""
        self._cleanup_expired()
        
        key = self._generate_key(product_name)
        cache_entry = self.cache.get(key)
        
        if cache_entry and not self._is_expired(cache_entry):
            return cache_entry["data"]
        
        # 如果快取不存在或已過期，移除它
        if key in self.cache:
            del self.cache[key]
        
        return None
    
    def set(self, product_name: str, data: Dict[str, Any]):
        """設定快取資料"""
        self._cleanup_expired()
        self._manage_size()
        
        key = self._generate_key(product_name)
        expires_at = datetime.now() + timedelta(minutes=self.expire_minutes)
        
        self.cache[key] = {
            "data": data,
            "created_at": datetime.now(),
            "expires_at": expires_at
        }
    
    def clear(self):
        """清空所有快取"""
        self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """取得快取統計資訊"""
        self._cleanup_expired()
        return {
            "total_items": len(self.cache),
            "max_size": self.max_size,
            "expire_minutes": self.expire_minutes
        } 