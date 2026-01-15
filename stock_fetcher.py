"""股票数据获取模块 - 获取实时价格和历史走势"""
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
from config import Config
from database import db

# 尝试导入akshare（用于A股和期货数据）
try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False
    print("⚠️ 未安装akshare库，A股和期货数据功能将不可用。安装命令：pip install akshare")


class StockFetcher:
    """股票数据获取类"""
    
    def __init__(self):
        self.alpha_vantage_key = Config.ALPHA_VANTAGE_API_KEY
        self.user_agent = Config.USER_AGENT
    
    def _detect_stock_type(self, symbol: str) -> str:
        """自动检测股票类型"""
        symbol_upper = symbol.upper()
        # A股：6位数字
        if symbol_upper.isdigit() and len(symbol_upper) == 6:
            return "a_stock"
        # 期货：通常是2-4个字母
        elif symbol_upper.isalpha() and len(symbol_upper) <= 4:
            # 常见期货代码
            futures_codes = ["AG", "AU", "CU", "AL", "ZN", "PB", "NI", "SN", "RB", "HC", "BU", "RU", 
                           "FU", "SP", "NR", "I", "J", "JM", "JD", "L", "V", "PP", "C", "CS", "A", 
                           "B", "M", "Y", "P", "CF", "CY", "SR", "TA", "OI", "MA", "FG", "RS", "RM",
                           "ZC", "WH", "PM", "RI", "LR", "JR", "SF", "SM", "UR", "SA", "PF", "PK"]
            if symbol_upper in futures_codes:
                return "futures"
        # 默认美股
        return "us_stock"
    
    def fetch_realtime_price(
        self,
        symbol: str,
        stock_type: Optional[str] = None
    ) -> Optional[Dict]:
        """获取股票实时价格"""
        if stock_type is None:
            stock_type = self._detect_stock_type(symbol)
        
        # 根据类型选择不同的数据源
        if stock_type == "a_stock":
            return self._fetch_a_stock_price(symbol)
        elif stock_type == "futures":
            return self._fetch_futures_price(symbol)
        else:
            # 美股使用Alpha Vantage
            return self._fetch_us_stock_price(symbol)
    
    def _fetch_us_stock_price(
        self,
        symbol: str
    ) -> Optional[Dict]:
        """获取美股实时价格（使用Alpha Vantage）"""
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
                "stock_type": "us_stock",
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
            print(f"获取美股 {symbol} 实时价格出错: {e}")
            return None
    
    def _fetch_a_stock_price(
        self,
        symbol: str
    ) -> Optional[Dict]:
        """获取A股实时价格（使用akshare）"""
        if not HAS_AKSHARE:
            print(f"⚠️ 无法获取A股 {symbol} 价格：未安装akshare库")
            return None
        
        try:
            # 判断是上交所还是深交所
            if symbol.startswith("6"):
                market = "SSE"  # 上交所
                symbol_with_suffix = f"sh{symbol}"
            elif symbol.startswith("0") or symbol.startswith("3"):
                market = "SZSE"  # 深交所
                symbol_with_suffix = f"sz{symbol}"
            else:
                print(f"⚠️ 无法识别A股代码 {symbol} 的市场")
                return None
            
            # 使用akshare获取实时行情
            df = ak.stock_zh_a_spot_em()
            stock_data = df[df["代码"] == symbol]
            
            if stock_data.empty:
                print(f"⚠️ 未找到A股代码 {symbol}")
                return None
            
            row = stock_data.iloc[0]
            
            # 计算涨跌幅
            current_price = self._safe_float(row.get("最新价"))
            change = self._safe_float(row.get("涨跌额"))
            change_percent = self._safe_float(row.get("涨跌幅"))
            volume = self._safe_int(row.get("成交量"))
            
            price_data = {
                "symbol": symbol,
                "stock_type": "a_stock",
                "price": current_price,
                "change": change,
                "change_percent": change_percent,
                "volume": volume,
                "market": market,
                "timestamp": datetime.utcnow(),
                "source": "akshare"
            }
            
            # 保存到数据库
            db.add_stock_price(price_data)
            
            return price_data
        except Exception as e:
            print(f"获取A股 {symbol} 实时价格出错: {e}")
            return None
    
    def _fetch_futures_price(
        self,
        symbol: str
    ) -> Optional[Dict]:
        """获取期货实时价格（使用akshare）"""
        if not HAS_AKSHARE:
            print(f"⚠️ 无法获取期货 {symbol} 价格：未安装akshare库")
            return None
        
        try:
            symbol_upper = symbol.upper()
            
            # 期货代码到交易所的映射
            futures_exchange_map = {
                # 上期所 (SHFE)
                "AG": "SHFE", "AU": "SHFE", "CU": "SHFE", "AL": "SHFE", 
                "ZN": "SHFE", "PB": "SHFE", "NI": "SHFE", "SN": "SHFE",
                "RB": "SHFE", "HC": "SHFE", "BU": "SHFE", "RU": "SHFE",
                "FU": "SHFE", "SP": "SHFE", "NR": "SHFE",
                # 大商所 (DCE)
                "I": "DCE", "J": "DCE", "JM": "DCE", "JD": "DCE",
                "L": "DCE", "V": "DCE", "PP": "DCE", "C": "DCE",
                "CS": "DCE", "A": "DCE", "B": "DCE", "M": "DCE",
                "Y": "DCE", "P": "DCE",
                # 郑商所 (CZCE)
                "CF": "CZCE", "CY": "CZCE", "SR": "CZCE", "TA": "CZCE",
                "OI": "CZCE", "MA": "CZCE", "FG": "CZCE", "RS": "CZCE",
                "RM": "CZCE", "ZC": "CZCE", "WH": "CZCE", "PM": "CZCE",
                "RI": "CZCE", "LR": "CZCE", "JR": "CZCE", "SF": "CZCE",
                "SM": "CZCE", "UR": "CZCE", "SA": "CZCE", "PF": "CZCE",
                "PK": "CZCE",
            }
            
            exchange = futures_exchange_map.get(symbol_upper, "SHFE")
            
            # 尝试获取期货主力合约数据
            try:
                # 获取期货主力合约列表
                futures_list = ak.futures_main_sina()
                
                if futures_list.empty:
                    print(f"⚠️ 无法获取期货列表")
                    return None
                
                # 查找匹配的期货（通过代码前缀匹配）
                symbol_lower = symbol.lower()
                futures_data = futures_list[
                    futures_list["symbol"].str.startswith(symbol_lower, na=False) |
                    futures_list["symbol"].str.startswith(symbol_upper, na=False)
                ]
                
                if futures_data.empty:
                    print(f"⚠️ 未找到期货代码 {symbol}")
                    return None
                
                # 取第一个匹配的（通常是主力合约）
                row = futures_data.iloc[0]
                futures_symbol = row["symbol"]
                
                # 获取实时行情
                quote = ak.futures_zh_realtime_sina(symbol=futures_symbol)
                
                if quote.empty or len(quote) == 0:
                    print(f"⚠️ 无法获取期货 {futures_symbol} 的实时行情")
                    return None
                
                quote_row = quote.iloc[0]
                
                # 获取价格数据（字段名可能因akshare版本而异）
                current_price = None
                change = None
                change_percent = None
                volume = None
                
                # 尝试不同的字段名
                price_fields = ["current_price", "最新价", "price", "现价"]
                change_fields = ["change", "涨跌", "涨跌额"]
                percent_fields = ["change_percent", "涨跌幅", "涨跌%"]
                volume_fields = ["volume", "成交量", "vol"]
                
                for field in price_fields:
                    if field in quote_row:
                        current_price = self._safe_float(quote_row[field])
                        break
                
                for field in change_fields:
                    if field in quote_row:
                        change = self._safe_float(quote_row[field])
                        break
                
                for field in percent_fields:
                    if field in quote_row:
                        change_percent = self._safe_float(quote_row[field])
                        break
                
                for field in volume_fields:
                    if field in quote_row:
                        volume = self._safe_int(quote_row[field])
                        break
                
                if current_price is None:
                    print(f"⚠️ 无法解析期货 {futures_symbol} 的价格数据")
                    return None
                
                price_data = {
                    "symbol": symbol_upper,
                    "stock_type": "futures",
                    "price": current_price,
                    "change": change,
                    "change_percent": change_percent,
                    "volume": volume,
                    "market": exchange,
                    "timestamp": datetime.utcnow(),
                    "source": "akshare"
                }
                
                # 保存到数据库
                db.add_stock_price(price_data)
                
                return price_data
            except Exception as e:
                print(f"获取期货 {symbol} 价格时出错: {e}")
                import traceback
                traceback.print_exc()
                return None
        except Exception as e:
            print(f"获取期货 {symbol} 实时价格出错: {e}")
            import traceback
            traceback.print_exc()
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
