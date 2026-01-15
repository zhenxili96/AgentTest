"""数据库模型和操作"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, func, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta
from typing import List, Optional
from config import Config

Base = declarative_base()


class Article(Base):
    """文章模型"""
    __tablename__ = "articles"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    content = Column(Text)
    url = Column(String(1000), unique=True, nullable=False, index=True)
    source = Column(String(200), nullable=False)
    author = Column(String(200))
    published_at = Column(DateTime, nullable=False, index=True)
    
    # 置信度评估结果
    confidence_score = Column(Float, nullable=False, index=True)
    relevance_score = Column(Float, nullable=False)
    reliability_score = Column(Float, nullable=False)
    ai_analysis = Column(Text)  # AI分析摘要
    
    # 元数据
    keywords = Column(String(500))  # 匹配的关键词
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_high_confidence = Column(Boolean, default=False, index=True)
    
    def __repr__(self):
        return f"<Article(id={self.id}, title='{self.title[:50]}...', confidence={self.confidence_score})>"


class MinedKeyword(Base):
    """挖掘的关键词模型"""
    __tablename__ = "mined_keywords"
    
    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(200), nullable=False, index=True)
    relevance_score = Column(Float, nullable=False, index=True)
    impact = Column(String(50))  # 上涨/下跌/中性/不确定
    reasoning = Column(Text)  # 分析说明
    source = Column(String(100))  # 来源：ai_analysis, manual, etc.
    is_active = Column(Boolean, default=True, index=True)  # 是否启用
    usage_count = Column(Integer, default=0)  # 使用次数
    mined_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    last_used_at = Column(DateTime)  # 最后使用时间
    
    def __repr__(self):
        return f"<MinedKeyword(id={self.id}, keyword='{self.keyword}', relevance={self.relevance_score})>"


class IdentifiedStock(Base):
    """识别的股票模型"""
    __tablename__ = "identified_stocks"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)  # 股票代码（支持更长代码如A股）
    company_name = Column(String(200))  # 公司名称
    stock_type = Column(String(20), default="us_stock", index=True)  # 类型：us_stock, a_stock, futures
    market = Column(String(50))  # 市场：NYSE, NASDAQ, SSE, SZSE, SHFE, DCE, CZCE, CFFEX等
    relevance = Column(Text)  # 与主题的相关性说明
    theme = Column(String(100))  # 关联的主题
    source = Column(String(100))  # 来源：ai_analysis, manual, etc.
    is_active = Column(Boolean, default=True, index=True)  # 是否启用
    identified_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    last_updated_at = Column(DateTime)  # 最后更新时间
    
    def __repr__(self):
        return f"<IdentifiedStock(id={self.id}, symbol='{self.symbol}', type='{self.stock_type}', company='{self.company_name}')>"


class StockPrice(Base):
    """股票价格历史模型"""
    __tablename__ = "stock_prices"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)  # 股票代码
    stock_type = Column(String(20), default="us_stock", index=True)  # 类型：us_stock, a_stock, futures
    price = Column(Float, nullable=False)  # 价格
    change = Column(Float)  # 涨跌额
    change_percent = Column(Float)  # 涨跌幅
    volume = Column(Integer)  # 成交量
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)  # 时间戳
    source = Column(String(100))  # 数据来源
    
    def __repr__(self):
        return f"<StockPrice(id={self.id}, symbol='{self.symbol}', type='{self.stock_type}', price={self.price}, timestamp={self.timestamp})>"


class Database:
    """数据库操作类"""
    
    def __init__(self):
        self.engine = create_engine(Config.DATABASE_URL, echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()
    
    def add_article(self, article_data: dict) -> Optional[Article]:
        """添加文章（如果不存在）"""
        session = self.get_session()
        try:
            # 检查URL是否已存在
            existing = session.query(Article).filter_by(url=article_data["url"]).first()
            if existing:
                return None
            
            article = Article(**article_data)
            session.add(article)
            session.commit()
            session.refresh(article)
            return article
        except Exception as e:
            session.rollback()
            print(f"添加文章时出错: {e}")
            return None
        finally:
            session.close()
    
    def get_high_confidence_articles(
        self, 
        limit: int = 50,
        min_score: Optional[float] = None,
        keywords: Optional[List[str]] = None
    ) -> List[Article]:
        """获取高置信度文章"""
        session = self.get_session()
        try:
            query = session.query(Article).filter(Article.is_high_confidence == True)
            
            if min_score:
                query = query.filter(Article.confidence_score >= min_score)

            if keywords:
                query = self._apply_keyword_filter(query, keywords)
            
            return query.order_by(Article.confidence_score.desc(), Article.published_at.desc()).limit(limit).all()
        finally:
            session.close()
    
    def get_recent_articles(
        self,
        hours: int = 24,
        limit: int = 100,
        keywords: Optional[List[str]] = None
    ) -> List[Article]:
        """获取最近的文章"""
        session = self.get_session()
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            query = session.query(Article)\
                .filter(Article.published_at >= cutoff_time)\
                .order_by(Article.published_at.desc())

            if keywords:
                query = self._apply_keyword_filter(query, keywords)

            return query.limit(limit).all()
        finally:
            session.close()
    
    def get_article_stats(self) -> dict:
        """获取文章统计信息"""
        session = self.get_session()
        try:
            total = session.query(Article).count()
            high_confidence = session.query(Article).filter(Article.is_high_confidence == True).count()
            avg_confidence = session.query(func.avg(Article.confidence_score)).scalar() or 0
            
            return {
                "total_articles": total,
                "high_confidence_articles": high_confidence,
                "average_confidence": float(avg_confidence),
            }
        finally:
            session.close()
    
    def _is_invalid_keyword(self, keyword: str) -> bool:
        """检查关键词是否是无效的占位符或示例关键词（与KeywordMiner中的逻辑保持一致）"""
        import re
        
        if not keyword or len(keyword.strip()) < 2:
            return True
        
        keyword_lower = keyword.lower().strip()
        keyword_original = keyword.strip()
        
        # 检查是否是占位符模式
        placeholder_patterns = [
            r'^关键词\d+$',
            r'^keyword\d+$',
            r'^example\d+$',
            r'^示例\d+$',
            r'^关键词\s*\d+$',
            r'^keyword\s*\d+$',
            r'^示例\s*\d+$',
            r'^example\s*\d+$',
            r'^关键词[一二三四五六七八九十]+$',
            r'^示例[一二三四五六七八九十]+$',
            r'^kw\d+$',
            r'^key\d+$',
            r'^词\d+$',
        ]
        
        for pattern in placeholder_patterns:
            if re.match(pattern, keyword_lower):
                return True
        
        # 检查是否是明显的示例或占位符文本
        invalid_texts = [
            '关键词', 'keyword', 'example', '示例', 'placeholder',
            '占位符', 'test', '测试', 'demo', '演示',
            '关键词1', '关键词2', '关键词3', '关键词4', '关键词5',
            'keyword1', 'keyword2', 'keyword3', 'keyword4', 'keyword5',
            'example1', 'example2', 'example3', 'example4', 'example5',
            '示例1', '示例2', '示例3',
            'kw1', 'kw2', 'kw3',
            'key1', 'key2', 'key3',
            '词1', '词2', '词3',
        ]
        
        if keyword_lower in invalid_texts:
            return True
        
        # 检查是否只包含数字或特殊字符
        if re.match(r'^[\d\s\-_\.]+$', keyword_original):
            return True
        
        # 检查是否包含明显的占位符标记
        if re.match(r'^(xxx|aaa|bbb|ccc|ddd|eee|fff|test|测试|示例|关键词)\d*$', keyword_lower):
            return True
        
        # 检查是否太短且只包含常见占位符词
        if len(keyword_original) <= 5:
            placeholder_words = ['关键词', 'keyword', 'example', '示例', 'test', '测试', 'demo', '演示']
            if keyword_lower in placeholder_words:
                return True
        
        return False
    
    def add_mined_keyword(self, keyword_data: dict) -> Optional[MinedKeyword]:
        """添加或更新挖掘的关键词"""
        session = self.get_session()
        try:
            keyword = keyword_data.get("keyword")
            if not keyword:
                return None
            
            # 验证关键词是否有效（防止无效关键词被保存）
            if self._is_invalid_keyword(keyword):
                print(f"⚠️ 拒绝保存无效关键词: {keyword}")
                return None
            
            # 检查是否已存在
            existing = session.query(MinedKeyword).filter_by(keyword=keyword).first()
            
            # 定义MinedKeyword模型的有效字段
            valid_fields = {
                "keyword", "relevance_score", "impact", "reasoning", 
                "source", "is_active", "usage_count", "mined_at", "last_used_at"
            }
            
            # 过滤掉无效字段（如validation_score等）
            filtered_data = {k: v for k, v in keyword_data.items() if k in valid_fields}
            
            if existing:
                # 更新现有记录（如果新记录的分数更高）
                if filtered_data.get("relevance_score", 0) > existing.relevance_score:
                    existing.relevance_score = filtered_data.get("relevance_score", existing.relevance_score)
                    existing.impact = filtered_data.get("impact", existing.impact)
                    existing.reasoning = filtered_data.get("reasoning", existing.reasoning)
                    existing.source = filtered_data.get("source", existing.source)
                    existing.is_active = filtered_data.get("is_active", existing.is_active)
                session.commit()
                session.refresh(existing)
                return existing
            else:
                # 创建新记录
                keyword_obj = MinedKeyword(**filtered_data)
                session.add(keyword_obj)
                session.commit()
                session.refresh(keyword_obj)
                return keyword_obj
        except Exception as e:
            session.rollback()
            print(f"添加挖掘关键词时出错: {e}")
            return None
        finally:
            session.close()
    
    def get_mined_keywords(
        self,
        is_active: Optional[bool] = None,
        min_relevance: Optional[float] = None,
        limit: int = 100
    ) -> List[MinedKeyword]:
        """获取挖掘的关键词"""
        session = self.get_session()
        try:
            query = session.query(MinedKeyword)
            
            if is_active is not None:
                query = query.filter(MinedKeyword.is_active == is_active)
            
            if min_relevance is not None:
                query = query.filter(MinedKeyword.relevance_score >= min_relevance)
            
            return query.order_by(
                MinedKeyword.relevance_score.desc(),
                MinedKeyword.mined_at.desc()
            ).limit(limit).all()
        finally:
            session.close()
    
    def update_keyword_usage(self, keyword: str):
        """更新关键词使用次数"""
        session = self.get_session()
        try:
            keyword_obj = session.query(MinedKeyword).filter_by(keyword=keyword).first()
            if keyword_obj:
                keyword_obj.usage_count = (keyword_obj.usage_count or 0) + 1
                keyword_obj.last_used_at = datetime.utcnow()
                session.commit()
        except Exception as e:
            session.rollback()
            print(f"更新关键词使用次数时出错: {e}")
        finally:
            session.close()
    
    def clean_invalid_keywords(self) -> dict:
        """清理数据库中无效的关键词"""
        session = self.get_session()
        try:
            # 获取所有关键词
            all_keywords = session.query(MinedKeyword).all()
            
            invalid_keywords = []
            for kw in all_keywords:
                if self._is_invalid_keyword(kw.keyword):
                    invalid_keywords.append(kw)
            
            # 删除无效关键词
            deleted_count = 0
            for kw in invalid_keywords:
                print(f"🗑️ 删除无效关键词: {kw.keyword} (ID: {kw.id})")
                session.delete(kw)
                deleted_count += 1
            
            session.commit()
            
            return {
                "total_keywords": len(all_keywords),
                "invalid_keywords": len(invalid_keywords),
                "deleted_count": deleted_count,
                "remaining_keywords": len(all_keywords) - deleted_count
            }
        except Exception as e:
            session.rollback()
            print(f"清理无效关键词时出错: {e}")
            return {
                "total_keywords": 0,
                "invalid_keywords": 0,
                "deleted_count": 0,
                "remaining_keywords": 0,
                "error": str(e)
            }
        finally:
            session.close()
    
    def get_invalid_keywords(self) -> List[MinedKeyword]:
        """获取数据库中无效的关键词列表（不删除，仅查询）"""
        session = self.get_session()
        try:
            all_keywords = session.query(MinedKeyword).all()
            invalid_keywords = [
                kw for kw in all_keywords 
                if self._is_invalid_keyword(kw.keyword)
            ]
            return invalid_keywords
        finally:
            session.close()

    def _apply_keyword_filter(self, query, keywords: List[str]):
        """为文章查询应用关键词过滤"""
        keyword_filters = []
        for keyword in keywords:
            if not keyword:
                continue
            like_pattern = f"%{keyword}%"
            keyword_filters.append(Article.title.ilike(like_pattern))
            keyword_filters.append(Article.content.ilike(like_pattern))
            keyword_filters.append(Article.keywords.ilike(like_pattern))

        if keyword_filters:
            query = query.filter(or_(*keyword_filters))
        return query
    
    def add_identified_stock(self, stock_data: dict) -> Optional[IdentifiedStock]:
        """添加或更新识别的股票"""
        session = self.get_session()
        try:
            symbol = stock_data.get("symbol", "").upper()
            if not symbol:
                return None
            
            # 检查是否已存在
            existing = session.query(IdentifiedStock).filter_by(symbol=symbol).first()
            
            valid_fields = {
                "symbol", "company_name", "stock_type", "market", "relevance", "theme", 
                "source", "is_active", "identified_at", "last_updated_at"
            }
            
            filtered_data = {k: v for k, v in stock_data.items() if k in valid_fields}
            filtered_data["symbol"] = symbol
            
            if existing:
                # 更新现有记录
                existing.company_name = filtered_data.get("company_name", existing.company_name)
                existing.stock_type = filtered_data.get("stock_type", existing.stock_type)
                existing.market = filtered_data.get("market", existing.market)
                existing.relevance = filtered_data.get("relevance", existing.relevance)
                existing.theme = filtered_data.get("theme", existing.theme)
                existing.source = filtered_data.get("source", existing.source)
                existing.is_active = filtered_data.get("is_active", existing.is_active)
                existing.last_updated_at = datetime.utcnow()
                session.commit()
                session.refresh(existing)
                return existing
            else:
                # 创建新记录
                stock_obj = IdentifiedStock(**filtered_data)
                session.add(stock_obj)
                session.commit()
                session.refresh(stock_obj)
                return stock_obj
        except Exception as e:
            session.rollback()
            print(f"添加识别股票时出错: {e}")
            return None
        finally:
            session.close()
    
    def get_identified_stocks(
        self,
        is_active: Optional[bool] = None,
        theme: Optional[str] = None,
        stock_type: Optional[str] = None,
        limit: int = 100
    ) -> List[IdentifiedStock]:
        """获取识别的股票列表"""
        session = self.get_session()
        try:
            query = session.query(IdentifiedStock)
            
            if is_active is not None:
                query = query.filter(IdentifiedStock.is_active == is_active)
            
            if theme:
                query = query.filter(IdentifiedStock.theme == theme)
            
            if stock_type:
                query = query.filter(IdentifiedStock.stock_type == stock_type)
            
            return query.order_by(
                IdentifiedStock.identified_at.desc()
            ).limit(limit).all()
        finally:
            session.close()
    
    def add_stock_price(self, price_data: dict) -> Optional[StockPrice]:
        """添加股票价格记录"""
        session = self.get_session()
        try:
            symbol = price_data.get("symbol", "").upper()
            if not symbol:
                return None
            
            price_obj = StockPrice(
                symbol=symbol,
                stock_type=price_data.get("stock_type", "us_stock"),
                price=price_data.get("price"),
                change=price_data.get("change"),
                change_percent=price_data.get("change_percent"),
                volume=price_data.get("volume"),
                timestamp=price_data.get("timestamp", datetime.utcnow()),
                source=price_data.get("source", "unknown")
            )
            session.add(price_obj)
            session.commit()
            session.refresh(price_obj)
            return price_obj
        except Exception as e:
            session.rollback()
            print(f"添加股票价格时出错: {e}")
            return None
        finally:
            session.close()
    
    def get_stock_prices(
        self,
        symbol: str,
        hours: int = 24,
        limit: int = 100
    ) -> List[StockPrice]:
        """获取股票价格历史"""
        session = self.get_session()
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            return session.query(StockPrice)\
                .filter(StockPrice.symbol == symbol.upper())\
                .filter(StockPrice.timestamp >= cutoff_time)\
                .order_by(StockPrice.timestamp.desc())\
                .limit(limit).all()
        finally:
            session.close()
    
    def get_latest_stock_price(self, symbol: str) -> Optional[StockPrice]:
        """获取股票最新价格"""
        session = self.get_session()
        try:
            return session.query(StockPrice)\
                .filter(StockPrice.symbol == symbol.upper())\
                .order_by(StockPrice.timestamp.desc())\
                .first()
        finally:
            session.close()


# 全局数据库实例
db = Database()
