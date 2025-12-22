import requests
from typing import Optional, Dict
from fastapi import HTTPException
from datetime import datetime, timedelta
from .database import get_db
from sqlalchemy.orm import Session

class CurrencyExchangeService:
    """
    货币兑换服务，提供实时汇率查询和货币转换功能
    """
    
    BASE_URL = "https://api.exchangerate-api.com/v4/latest/"
    CACHE_EXPIRY = timedelta(hours=1)
    
    def __init__(self):
        self._rates_cache = {}
        self._last_updated = {}
    
    def _is_cache_valid(self, base_currency: str) -> bool:
        """检查缓存是否有效"""
        if base_currency not in self._last_updated:
            return False
        return datetime.now() - self._last_updated[base_currency] < self.CACHE_EXPIRY
    
    def _fetch_exchange_rates(self, base_currency: str) -> Dict[str, float]:
        """从API获取实时汇率"""
        try:
            response = requests.get(f"{self.BASE_URL}{base_currency}")
            response.raise_for_status()
            data = response.json()
            
            if not data.get('rates'):
                raise HTTPException(status_code=500, detail="Invalid API response")
                
            self._rates_cache[base_currency] = data['rates']
            self._last_updated[base_currency] = datetime.now()
            return data['rates']
            
        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to fetch exchange rates: {str(e)}"
            )
    
    def get_exchange_rate(self, base_currency: str, target_currency: str) -> float:
        """
        获取两种货币之间的汇率
        
        Args:
            base_currency: 基础货币代码 (如 USD)
            target_currency: 目标货币代码 (如 CNY)
            
        Returns:
            汇率值 (1单位基础货币 = X单位目标货币)
        """
        if base_currency == target_currency:
            return 1.0
            
        if not self._is_cache_valid(base_currency):
            self._fetch_exchange_rates(base_currency)
            
        rates = self._rates_cache.get(base_currency, {})
        if target_currency not in rates:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported target currency: {target_currency}"
            )
            
        return rates[target_currency]
    
    def convert_currency(
        self, 
        amount: float, 
        from_currency: str, 
        to_currency: str,
        db: Session = next(get_db())
    ) -> float:
        """
        货币转换
        
        Args:
            amount: 要转换的金额
            from_currency: 原始货币代码
            to_currency: 目标货币代码
            db: 数据库会话 (用于记录转换记录)
            
        Returns:
            转换后的金额
        """
        try:
            rate = self.get_exchange_rate(from_currency, to_currency)
            converted_amount = amount * rate
            
            # 这里可以添加数据库记录逻辑
            # 例如记录转换历史记录
            
            return round(converted_amount, 2)
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Currency conversion failed: {str(e)}"
            )

# 单例模式，全局共享一个实例
exchange_service = CurrencyExchangeService()