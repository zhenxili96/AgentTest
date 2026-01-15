"""股票数据获取模块 - 获取实时价格和历史走势"""
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
from config import Config
from database import db


class StockFetcher:
    """股票数据获取类"""
    
    def __init__(self):
        self.alpha_vantage_key = Config.ALPHA_VANTAGE_API_KEY
        self.user_agent = Config.USER_AGENT
    
    def fetch_realtime_price(
        self,
        symbol: str
    ) -> Optional[Dict]:
        """获取股票实时价格"""
        if not self.alpha_vantage_key:
            return None
        
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol.upper(),
                "apikey": self.alpha_vantage_key,
            }
            headers = {"User-Agent": self.user_agent}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "Note" in data:
                print(f"⚠️ Alpha Vantage API限制: {data.get('Note')}")
                return None
            
            quote = data.get("Global Quote", {}) or {}
            if not quote:
                return None
            
            price_data = {
                "symbol": quote.get("01. symbol", symbol.upper()),
                "price": self._safe_float(quote.get("05. price")),
                "change": self._safe_float(quote.get("09. change")),
                "change_percent": self._parse_percent(quote.get("10. change percent", "")),
                "volume": self._safe_int(quote.get("06. volume")),
                "latest_trading_day": quote.get("07. latest trading day", ""),
                "timestamp": datetime.utcnow(),
                "source": "Alpha Vantage"
            }
            
            # 保存到数据库
            db.add_stock_price(price_data)
            
            return price_data
        except Exception as e:
            print(f"获取股票 {symbol} 实时价格出错: {e}")
            return None
    
    def fetch_intraday_data(
        self,
        symbol: str,
        interval: str = "5min"
    ) -> Optional[List[Dict]]:
        """获取股票日内数据（用于走势图）"""
        if not self.alpha_vantage_key:
            return None
        
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                "function": "TIME_SERIES_INTRADAY",
                "symbol": symbol.upper(),
                "interval": interval,
                "apikey": self.alpha_vantage_key,
                "outputsize": "compact"  # compact返回最近100个数据点
            }
            headers = {"User-Agent": self.user_agent}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "Note" in data:
                print(f"⚠️ Alpha Vantage API限制: {data.get('Note')}")
                return None
            
            # Alpha Vantage返回的数据格式
            time_series_key = f"Time Series ({interval})"
            if time_series_key not in data:
                return None
            
            time_series = data[time_series_key]
            prices = []
            
            for timestamp_str, values in time_series.items():
                try:
                    # 解析时间戳
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    
                    prices.append({
                        "timestamp": timestamp.isoformat(),
                        "open": self._safe_float(values.get("1. open")),
                        "high": self._safe_float(values.get("2. high")),
                        "low": self._safe_float(values.get("3. low")),
                        "close": self._safe_float(values.get("4. close")),
                        "volume": self._safe_int(values.get("5. volume")),
                    })
                except Exception as e:
                    continue
            
            # 按时间排序（从旧到新）
            prices.sort(key=lambda x: x["timestamp"])
            
            return prices
        except Exception as e:
            print(f"获取股票 {symbol} 日内数据出错: {e}")
            return None
    
    def fetch_daily_data(
        self,
        symbol: str,
        days: int = 30
    ) -> Optional[List[Dict]]:
        """获取股票日线数据"""
        if not self.alpha_vantage_key:
            return None
        
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol.upper(),
                "apikey": self.alpha_vantage_key,
                "outputsize": "compact" if days <= 100 else "full"
            }
            headers = {"User-Agent": self.user_agent}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "Note" in data:
                print(f"⚠️ Alpha Vantage API限制: {data.get('Note')}")
                return None
            
            if "Time Series (Daily)" not in data:
                return None
            
            time_series = data["Time Series (Daily)"]
            prices = []
            
            for timestamp_str, values in list(time_series.items())[:days]:
                try:
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d")
                    
                    prices.append({
                        "timestamp": timestamp.isoformat(),
                        "open": self._safe_float(values.get("1. open")),
                        "high": self._safe_float(values.get("2. high")),
                        "low": self._safe_float(values.get("3. low")),
                        "close": self._safe_float(values.get("4. close")),
                        "volume": self._safe_int(values.get("5. volume")),
                    })
                except Exception as e:
                    continue
            
            # 按时间排序（从旧到新）
            prices.sort(key=lambda x: x["timestamp"])
            
            return prices
        except Exception as e:
            print(f"获取股票 {symbol} 日线数据出错: {e}")
            return None
    
    def fetch_multiple_stocks(
        self,
        symbols: List[str]
    ) -> Dict[str, Optional[Dict]]:
        """批量获取多个股票的实时价格"""
        results = {}
        for symbol in symbols:
            results[symbol] = self.fetch_realtime_price(symbol)
            # 避免API频率限制，添加短暂延迟
            import time
            time.sleep(0.2)
        return results
    
    @staticmethod
    def _safe_float(value: Optional[str]) -> Optional[float]:
        """安全解析浮点数"""
        try:
            return float(value) if value not in (None, "") else None
        except (TypeError, ValueError):
            return None
    
    @staticmethod
    def _safe_int(value: Optional[str]) -> Optional[int]:
        """安全解析整数"""
        try:
            return int(float(value)) if value not in (None, "") else None
        except (TypeError, ValueError):
            return None
    
    @staticmethod
    def _parse_percent(value: Optional[str]) -> Optional[float]:
        """解析百分比字符串（如 "1.23%"）"""
        if not value:
            return None
        try:
            # 移除百分号并转换为浮点数
            return float(value.replace("%", ""))
        except (TypeError, ValueError):
            return None
