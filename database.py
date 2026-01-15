"""数据库模型和操作"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, func
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
        min_score: Optional[float] = None
    ) -> List[Article]:
        """获取高置信度文章"""
        session = self.get_session()
        try:
            query = session.query(Article).filter(Article.is_high_confidence == True)
            
            if min_score:
                query = query.filter(Article.confidence_score >= min_score)
            
            return query.order_by(Article.confidence_score.desc(), Article.published_at.desc()).limit(limit).all()
        finally:
            session.close()
    
    def get_recent_articles(self, hours: int = 24, limit: int = 100) -> List[Article]:
        """获取最近的文章"""
        session = self.get_session()
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            return session.query(Article)\
                .filter(Article.published_at >= cutoff_time)\
                .order_by(Article.published_at.desc())\
                .limit(limit)\
                .all()
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
    
    def add_mined_keyword(self, keyword_data: dict) -> Optional[MinedKeyword]:
        """添加或更新挖掘的关键词"""
        session = self.get_session()
        try:
            keyword = keyword_data.get("keyword")
            if not keyword:
                return None
            
            # 检查是否已存在
            existing = session.query(MinedKeyword).filter_by(keyword=keyword).first()
            
            if existing:
                # 更新现有记录（如果新记录的分数更高）
                if keyword_data.get("relevance_score", 0) > existing.relevance_score:
                    existing.relevance_score = keyword_data.get("relevance_score", existing.relevance_score)
                    existing.impact = keyword_data.get("impact", existing.impact)
                    existing.reasoning = keyword_data.get("reasoning", existing.reasoning)
                    existing.source = keyword_data.get("source", existing.source)
                    existing.is_active = keyword_data.get("is_active", existing.is_active)
                session.commit()
                session.refresh(existing)
                return existing
            else:
                # 创建新记录
                keyword_obj = MinedKeyword(**keyword_data)
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


# 全局数据库实例
db = Database()
