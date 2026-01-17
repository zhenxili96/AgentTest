"""股票数据获取模块 - 获取实时价格和历史走势"""
import requests
import time
import random
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

# 尝试导入yfinance（Yahoo Finance数据源）
try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    print("⚠️ 未安装yfinance库，Yahoo Finance数据源将不可用。安装命令：pip install yfinance")

# 尝试导入finnhub（Finnhub数据源）
try:
    import finnhub
    HAS_FINNHUB = True
except ImportError:
    HAS_FINNHUB = False

# 尝试导入tushare（中国市场数据）
try:
    import tushare as ts
    HAS_TUSHARE = True
except ImportError:
    HAS_TUSHARE = False
    print("⚠️ 未安装tushare库，Tushare数据源将不可用。安装命令：pip install tushare")


class StockFetcher:
    """股票数据获取类 - 支持多数据源"""
    
    def __init__(self):
        self.alpha_vantage_key = Config.ALPHA_VANTAGE_API_KEY
        self.user_agent = Config.USER_AGENT
        
        # 初始化Finnhub客户端
        self.finnhub_client = None
        if HAS_FINNHUB and Config.FINNHUB_API_KEY:
            self.finnhub_client = finnhub.Client(api_key=Config.FINNHUB_API_KEY)
        
        # 初始化Tushare
        self.tushare_pro = None
        if HAS_TUSHARE and Config.TUSHARE_TOKEN:
            ts.set_token(Config.TUSHARE_TOKEN)
            self.tushare_pro = ts.pro_api()
        
        # 数据源优先级配置
        self.us_stock_sources = ["yfinance", "finnhub", "alpha_vantage"]
        self.a_stock_sources = ["akshare", "tushare"]
    
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
        """获取美股实时价格（多数据源备选）"""
        # 按优先级尝试各数据源
        for source in self.us_stock_sources:
            result = None
            try:
                if source == "yfinance":
                    result = self._fetch_yfinance_price(symbol)
                elif source == "finnhub" and self.finnhub_client:
                    result = self._fetch_finnhub_price(symbol)
                elif source == "alpha_vantage" and self.alpha_vantage_key:
                    result = self._fetch_alpha_vantage_price(symbol)
                
                if result:
                    return result
            except Exception as e:
                print(f"  ⚠️ {source} 获取 {symbol} 失败: {e}")
                continue
        
        return None
    
    def _fetch_yfinance_price(
        self,
        symbol: str,
        max_retries: int = 3
    ) -> Optional[Dict]:
        """使用yfinance获取股票价格（免费，带重试机制处理速率限制）"""
        if not HAS_YFINANCE:
            return None
        
        for attempt in range(max_retries):
            try:
                ticker = yf.Ticker(symbol.upper())
                info = ticker.info
                
                if not info or "regularMarketPrice" not in info:
                    # 尝试获取历史数据
                    hist = ticker.history(period="1d")
                    if hist.empty:
                        return None
                    
                    latest = hist.iloc[-1]
                    price_data = {
                        "symbol": symbol.upper(),
                        "stock_type": "us_stock",
                        "price": self._safe_float(latest.get("Close")),
                        "change": None,
                        "change_percent": None,
                        "volume": self._safe_int(latest.get("Volume")),
                        "timestamp": datetime.utcnow(),
                        "source": "yfinance"
                    }
                else:
                    # 计算涨跌幅
                    current_price = info.get("regularMarketPrice")
                    previous_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
                    change = None
                    change_percent = None
                    
                    if current_price and previous_close:
                        change = current_price - previous_close
                        change_percent = (change / previous_close) * 100
                    
                    price_data = {
                        "symbol": symbol.upper(),
                        "stock_type": "us_stock",
                        "price": self._safe_float(current_price),
                        "change": self._safe_float(change),
                        "change_percent": self._safe_float(change_percent),
                        "volume": self._safe_int(info.get("regularMarketVolume")),
                        "market_cap": self._safe_float(info.get("marketCap")),
                        "pe_ratio": self._safe_float(info.get("trailingPE")),
                        "fifty_two_week_high": self._safe_float(info.get("fiftyTwoWeekHigh")),
                        "fifty_two_week_low": self._safe_float(info.get("fiftyTwoWeekLow")),
                        "timestamp": datetime.utcnow(),
                        "source": "yfinance"
                    }
                
                # 保存到数据库
                db.add_stock_price(price_data)
                
                return price_data
            except Exception as e:
                error_msg = str(e).lower()
                # 检查是否是速率限制错误
                if "rate limit" in error_msg or "too many requests" in error_msg:
                    if attempt < max_retries - 1:
                        # 指数退避：2^attempt 秒 + 随机抖动
                        wait_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                        print(f"  ⏳ yfinance 速率限制，{wait_time:.1f}秒后重试 ({attempt + 1}/{max_retries})...")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"  ⚠️ yfinance 获取 {symbol} 达到重试上限，跳过")
                        return None
                else:
                    print(f"yfinance获取 {symbol} 出错: {e}")
                    return None
        
        return None
    
    def _fetch_finnhub_price(
        self,
        symbol: str
    ) -> Optional[Dict]:
        """使用Finnhub获取股票价格"""
        if not self.finnhub_client:
            return None
        
        try:
            quote = self.finnhub_client.quote(symbol.upper())
            
            if not quote or quote.get("c") is None:
                return None
            
            current_price = quote.get("c")  # current price
            previous_close = quote.get("pc")  # previous close
            change = quote.get("d")  # change
            change_percent = quote.get("dp")  # change percent
            
            price_data = {
                "symbol": symbol.upper(),
                "stock_type": "us_stock",
                "price": self._safe_float(current_price),
                "change": self._safe_float(change),
                "change_percent": self._safe_float(change_percent),
                "high": self._safe_float(quote.get("h")),
                "low": self._safe_float(quote.get("l")),
                "open": self._safe_float(quote.get("o")),
                "previous_close": self._safe_float(previous_close),
                "timestamp": datetime.utcnow(),
                "source": "Finnhub"
            }
            
            # 保存到数据库
            db.add_stock_price(price_data)
            
            return price_data
        except Exception as e:
            print(f"Finnhub获取 {symbol} 出错: {e}")
            return None
    
    def _fetch_alpha_vantage_price(
        self,
        symbol: str
    ) -> Optional[Dict]:
        """使用Alpha Vantage获取股票价格"""
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
            print(f"Alpha Vantage获取 {symbol} 出错: {e}")
            return None
    
    def _fetch_a_stock_price(
        self,
        symbol: str
    ) -> Optional[Dict]:
        """获取A股实时价格（多数据源备选）"""
        # 按优先级尝试各数据源
        for source in self.a_stock_sources:
            result = None
            try:
                if source == "akshare" and HAS_AKSHARE:
                    result = self._fetch_akshare_a_stock(symbol)
                elif source == "tushare" and self.tushare_pro:
                    result = self._fetch_tushare_a_stock(symbol)
                
                if result:
                    return result
            except Exception as e:
                print(f"  ⚠️ {source} 获取A股 {symbol} 失败: {e}")
                continue
        
        print(f"⚠️ 无法获取A股 {symbol} 价格：所有数据源均失败")
        return None
    
    def _fetch_akshare_a_stock(
        self,
        symbol: str
    ) -> Optional[Dict]:
        """使用akshare获取A股价格"""
        try:
            # 判断是上交所还是深交所
            if symbol.startswith("6"):
                market = "SSE"  # 上交所
            elif symbol.startswith("0") or symbol.startswith("3"):
                market = "SZSE"  # 深交所
            else:
                print(f"⚠️ 无法识别A股代码 {symbol} 的市场")
                return None
            
            # 使用akshare获取实时行情
            df = ak.stock_zh_a_spot_em()
            stock_data = df[df["代码"] == symbol]
            
            if stock_data.empty:
                return None
            
            row = stock_data.iloc[0]
            
            price_data = {
                "symbol": symbol,
                "stock_type": "a_stock",
                "price": self._safe_float(row.get("最新价")),
                "change": self._safe_float(row.get("涨跌额")),
                "change_percent": self._safe_float(row.get("涨跌幅")),
                "volume": self._safe_int(row.get("成交量")),
                "turnover": self._safe_float(row.get("成交额")),
                "high": self._safe_float(row.get("最高")),
                "low": self._safe_float(row.get("最低")),
                "open": self._safe_float(row.get("今开")),
                "market": market,
                "timestamp": datetime.utcnow(),
                "source": "akshare"
            }
            
            db.add_stock_price(price_data)
            return price_data
        except Exception as e:
            print(f"akshare获取A股 {symbol} 出错: {e}")
            return None
    
    def _fetch_tushare_a_stock(
        self,
        symbol: str
    ) -> Optional[Dict]:
        """使用Tushare获取A股价格"""
        if not self.tushare_pro:
            return None
        
        try:
            # 构建Tushare格式的股票代码
            if symbol.startswith("6"):
                ts_code = f"{symbol}.SH"
                market = "SSE"
            elif symbol.startswith("0") or symbol.startswith("3"):
                ts_code = f"{symbol}.SZ"
                market = "SZSE"
            else:
                return None
            
            # 获取当日行情
            today = datetime.now().strftime("%Y%m%d")
            df = self.tushare_pro.daily(ts_code=ts_code, start_date=today, end_date=today)
            
            if df.empty:
                # 尝试获取最近一个交易日的数据
                df = self.tushare_pro.daily(ts_code=ts_code, limit=1)
            
            if df.empty:
                return None
            
            row = df.iloc[0]
            
            price_data = {
                "symbol": symbol,
                "stock_type": "a_stock",
                "price": self._safe_float(row.get("close")),
                "change": self._safe_float(row.get("change")),
                "change_percent": self._safe_float(row.get("pct_chg")),
                "volume": self._safe_int(row.get("vol")),
                "turnover": self._safe_float(row.get("amount")),
                "high": self._safe_float(row.get("high")),
                "low": self._safe_float(row.get("low")),
                "open": self._safe_float(row.get("open")),
                "market": market,
                "timestamp": datetime.utcnow(),
                "source": "tushare"
            }
            
            db.add_stock_price(price_data)
            return price_data
        except Exception as e:
            print(f"Tushare获取A股 {symbol} 出错: {e}")
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
                
                # 检查DataFrame的实际列名（akshare可能返回不同的列名）
                # 可能的列名：symbol, 代码, 合约代码, name, 名称等
                symbol_column = None
                possible_symbol_columns = ["symbol", "代码", "合约代码", "name", "名称", "symbol_name"]
                for col in possible_symbol_columns:
                    if col in futures_list.columns:
                        symbol_column = col
                        break
                
                if symbol_column is None:
                    print(f"⚠️ 无法识别期货列表的代码列，可用列: {list(futures_list.columns)}")
                    return None
                
                # 查找匹配的期货（通过代码前缀匹配）
                symbol_lower = symbol.lower()
                futures_data = futures_list[
                    futures_list[symbol_column].str.startswith(symbol_lower, na=False) |
                    futures_list[symbol_column].str.startswith(symbol_upper, na=False)
                ]
                
                if futures_data.empty:
                    print(f"⚠️ 未找到期货代码 {symbol}")
                    return None
                
                # 取第一个匹配的（通常是主力合约）
                row = futures_data.iloc[0]
                futures_symbol = row[symbol_column]
                
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
        interval: str = "5m"
    ) -> Optional[List[Dict]]:
        """获取股票日内数据（用于走势图，优先使用yfinance）"""
        # 优先使用yfinance（免费且无限制）
        if HAS_YFINANCE:
            result = self._fetch_yfinance_intraday(symbol, interval)
            if result:
                return result
        
        # 备选使用Alpha Vantage
        if self.alpha_vantage_key:
            return self._fetch_alpha_vantage_intraday(symbol, interval)
        
        return None
    
    def _fetch_yfinance_intraday(
        self,
        symbol: str,
        interval: str = "5m"
    ) -> Optional[List[Dict]]:
        """使用yfinance获取日内数据"""
        try:
            ticker = yf.Ticker(symbol.upper())
            # yfinance支持的间隔：1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h
            hist = ticker.history(period="1d", interval=interval)
            
            if hist.empty:
                return None
            
            prices = []
            for timestamp, row in hist.iterrows():
                prices.append({
                    "timestamp": timestamp.isoformat(),
                    "open": self._safe_float(row.get("Open")),
                    "high": self._safe_float(row.get("High")),
                    "low": self._safe_float(row.get("Low")),
                    "close": self._safe_float(row.get("Close")),
                    "volume": self._safe_int(row.get("Volume")),
                })
            
            return prices
        except Exception as e:
            print(f"yfinance获取 {symbol} 日内数据出错: {e}")
            return None
    
    def _fetch_alpha_vantage_intraday(
        self,
        symbol: str,
        interval: str = "5min"
    ) -> Optional[List[Dict]]:
        """使用Alpha Vantage获取日内数据"""
        # 转换间隔格式（yfinance格式 -> Alpha Vantage格式）
        interval_map = {"1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min", "60m": "60min"}
        av_interval = interval_map.get(interval, interval)
        
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                "function": "TIME_SERIES_INTRADAY",
                "symbol": symbol.upper(),
                "interval": av_interval,
                "apikey": self.alpha_vantage_key,
                "outputsize": "compact"
            }
            headers = {"User-Agent": self.user_agent}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "Note" in data:
                print(f"⚠️ Alpha Vantage API限制: {data.get('Note')}")
                return None
            
            time_series_key = f"Time Series ({av_interval})"
            if time_series_key not in data:
                return None
            
            time_series = data[time_series_key]
            prices = []
            
            for timestamp_str, values in time_series.items():
                try:
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    prices.append({
                        "timestamp": timestamp.isoformat(),
                        "open": self._safe_float(values.get("1. open")),
                        "high": self._safe_float(values.get("2. high")),
                        "low": self._safe_float(values.get("3. low")),
                        "close": self._safe_float(values.get("4. close")),
                        "volume": self._safe_int(values.get("5. volume")),
                    })
                except Exception:
                    continue
            
            prices.sort(key=lambda x: x["timestamp"])
            return prices
        except Exception as e:
            print(f"Alpha Vantage获取 {symbol} 日内数据出错: {e}")
            return None
    
    def fetch_daily_data(
        self,
        symbol: str,
        days: int = 30
    ) -> Optional[List[Dict]]:
        """获取股票日线数据（优先使用yfinance）"""
        # 优先使用yfinance
        if HAS_YFINANCE:
            result = self._fetch_yfinance_daily(symbol, days)
            if result:
                return result
        
        # 备选使用Alpha Vantage
        if self.alpha_vantage_key:
            return self._fetch_alpha_vantage_daily(symbol, days)
        
        return None
    
    def _fetch_yfinance_daily(
        self,
        symbol: str,
        days: int = 30
    ) -> Optional[List[Dict]]:
        """使用yfinance获取日线数据"""
        try:
            ticker = yf.Ticker(symbol.upper())
            # 根据天数选择合适的period
            if days <= 5:
                period = "5d"
            elif days <= 30:
                period = "1mo"
            elif days <= 90:
                period = "3mo"
            elif days <= 180:
                period = "6mo"
            elif days <= 365:
                period = "1y"
            else:
                period = "2y"
            
            hist = ticker.history(period=period)
            
            if hist.empty:
                return None
            
            prices = []
            for timestamp, row in hist.tail(days).iterrows():
                prices.append({
                    "timestamp": timestamp.strftime("%Y-%m-%d"),
                    "open": self._safe_float(row.get("Open")),
                    "high": self._safe_float(row.get("High")),
                    "low": self._safe_float(row.get("Low")),
                    "close": self._safe_float(row.get("Close")),
                    "volume": self._safe_int(row.get("Volume")),
                })
            
            return prices
        except Exception as e:
            print(f"yfinance获取 {symbol} 日线数据出错: {e}")
            return None
    
    def _fetch_alpha_vantage_daily(
        self,
        symbol: str,
        days: int = 30
    ) -> Optional[List[Dict]]:
        """使用Alpha Vantage获取日线数据"""
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
                    prices.append({
                        "timestamp": timestamp_str,
                        "open": self._safe_float(values.get("1. open")),
                        "high": self._safe_float(values.get("2. high")),
                        "low": self._safe_float(values.get("3. low")),
                        "close": self._safe_float(values.get("4. close")),
                        "volume": self._safe_int(values.get("5. volume")),
                    })
                except Exception:
                    continue
            
            prices.sort(key=lambda x: x["timestamp"])
            return prices
        except Exception as e:
            print(f"Alpha Vantage获取 {symbol} 日线数据出错: {e}")
            return None
    
    def fetch_multiple_stocks(
        self,
        symbols: List[str]
    ) -> Dict[str, Optional[Dict]]:
        """批量获取多个股票的实时价格"""
        results = {}
        for i, symbol in enumerate(symbols):
            results[symbol] = self.fetch_realtime_price(symbol)
            # 避免API频率限制，添加延迟（每5个请求后增加额外延迟）
            if i < len(symbols) - 1:
                base_delay = 0.5 + random.uniform(0, 0.3)
                if (i + 1) % 5 == 0:
                    base_delay += 1.0  # 每5个请求后额外等待1秒
                time.sleep(base_delay)
        return results
    
    def fetch_commodity_price(
        self,
        commodity: str = "GC=F",
        max_retries: int = 3
    ) -> Optional[Dict]:
        """获取商品价格（黄金、白银等）
        
        常用商品代码（Yahoo Finance格式）：
        - GC=F: 黄金期货
        - SI=F: 白银期货
        - CL=F: WTI原油
        - BZ=F: 布伦特原油
        - HG=F: 铜期货
        - NG=F: 天然气
        """
        if not HAS_YFINANCE:
            return None
        
        for attempt in range(max_retries):
            try:
                ticker = yf.Ticker(commodity)
                info = ticker.info
                
                if not info:
                    return None
                
                current_price = info.get("regularMarketPrice") or info.get("previousClose")
                previous_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
                
                change = None
                change_percent = None
                if current_price and previous_close:
                    change = current_price - previous_close
                    change_percent = (change / previous_close) * 100
                
                return {
                    "symbol": commodity,
                    "name": info.get("shortName", commodity),
                    "price": self._safe_float(current_price),
                    "change": self._safe_float(change),
                    "change_percent": self._safe_float(change_percent),
                    "currency": info.get("currency", "USD"),
                    "market_state": info.get("marketState", ""),
                    "timestamp": datetime.utcnow(),
                    "source": "yfinance"
                }
            except Exception as e:
                error_msg = str(e).lower()
                if "rate limit" in error_msg or "too many requests" in error_msg:
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                        print(f"  ⏳ yfinance 速率限制，{wait_time:.1f}秒后重试 ({attempt + 1}/{max_retries})...")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"  ⚠️ 获取商品 {commodity} 达到重试上限，跳过")
                        return None
                else:
                    print(f"获取商品 {commodity} 价格出错: {e}")
                    return None
        
        return None
    
    def fetch_precious_metals(self) -> Dict[str, Optional[Dict]]:
        """获取贵金属价格（黄金、白银、铂金、钯金）"""
        metals = {
            "gold": "GC=F",      # 黄金
            "silver": "SI=F",    # 白银
            "platinum": "PL=F",  # 铂金
            "palladium": "PA=F", # 钯金
        }
        
        results = {}
        metal_list = list(metals.items())
        for i, (name, symbol) in enumerate(metal_list):
            results[name] = self.fetch_commodity_price(symbol)
            if i < len(metal_list) - 1:
                time.sleep(0.5 + random.uniform(0, 0.3))
        
        return results
    
    def fetch_stock_news(
        self,
        symbol: str,
        count: int = 10
    ) -> List[Dict]:
        """获取个股新闻（使用Finnhub）"""
        if not self.finnhub_client:
            return []
        
        try:
            # 获取最近7天的新闻
            from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            to_date = datetime.now().strftime("%Y-%m-%d")
            
            news = self.finnhub_client.company_news(
                symbol.upper(),
                _from=from_date,
                to=to_date
            )
            
            articles = []
            for item in news[:count]:
                articles.append({
                    "title": item.get("headline", ""),
                    "summary": item.get("summary", ""),
                    "url": item.get("url", ""),
                    "source": item.get("source", "Finnhub"),
                    "published_at": datetime.fromtimestamp(item.get("datetime", 0)),
                    "related": item.get("related", ""),
                    "image": item.get("image", ""),
                })
            
            return articles
        except Exception as e:
            print(f"获取 {symbol} 新闻出错: {e}")
            return []
    
    def get_available_sources(self) -> Dict[str, bool]:
        """获取当前可用的数据源状态"""
        return {
            "yfinance": HAS_YFINANCE,
            "finnhub": self.finnhub_client is not None,
            "alpha_vantage": bool(self.alpha_vantage_key),
            "akshare": HAS_AKSHARE,
            "tushare": self.tushare_pro is not None,
        }
    
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
