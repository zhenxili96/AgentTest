# NewsAPI不可用时的替代方案

## 问题说明

如果无法访问 [NewsAPI](https://newsapi.org/)（可能由于网络限制或地区限制），程序仍然可以正常工作。

## 解决方案

程序已经设计为**NewsAPI是可选的**，即使没有NewsAPI密钥，也可以使用RSS源获取新闻信息。

### 方案1：仅使用RSS源（推荐）

**无需任何额外配置**，程序已经内置了多个可靠的RSS源：

- Yahoo Finance（雅虎财经）
- CNBC（美国财经新闻）
- Reuters（路透社财经新闻）
- Bloomberg（彭博社）
- Financial Times（金融时报）

程序会自动从这些RSS源搜索与白银相关的新闻。

#### 配置步骤

1. 创建 `.env` 文件，**只需配置OpenAI API密钥**：

```env
# OpenAI API配置（必须）- 用于AI置信度评估
OPENAI_API_KEY=sk-your-openai-api-key-here

# NewsAPI配置（可选）- 不配置也可以，程序会使用RSS源
# NEWS_API_KEY=

# 其他配置（可选）
SEARCH_INTERVAL_MINUTES=30
MAX_ARTICLES_PER_SEARCH=50
MIN_CONFIDENCE_SCORE=0.7
```

2. 直接运行程序：

```bash
python main.py
```

程序会：
- 自动从RSS源搜索新闻
- 使用OpenAI评估置信度
- 保存高置信度信息到数据库

### 方案2：添加自定义RSS源

如果默认的RSS源无法访问，可以在 `config.py` 中添加自定义RSS源：

```python
RSS_FEEDS: List[str] = [
    "https://your-custom-rss-feed.com/rss",
    # 添加更多RSS源...
]
```

#### 常用中文财经RSS源（如果可访问）

虽然很多中文网站不直接提供RSS，但可以尝试：

1. **使用RSS聚合服务**：
   - 使用RSSHub等聚合服务转换
   - 例如：`https://rsshub.app/sina/finance`（如果RSSHub可用）

2. **直接使用搜索引擎RSS**：
   - Google News RSS（如果可访问）
   - 其他地区可访问的财经RSS源

### 方案3：使用代理访问NewsAPI

如果可以配置代理，可以在代码中设置代理来访问NewsAPI：

1. 修改 `search_engine.py` 中的 `search_newsapi` 方法
2. 添加代理配置到 `.env` 文件
3. 在requests请求中使用代理

## 功能对比

| 功能 | 使用NewsAPI | 仅使用RSS源 |
|------|------------|------------|
| 新闻搜索 | ✅ 强大，支持关键词搜索 | ✅ 通过关键词过滤 |
| 新闻数量 | ✅ 大量新闻源 | ⚠️ 受限于RSS源数量 |
| 实时性 | ✅ 非常实时 | ✅ 实时（取决于RSS更新频率） |
| 配置复杂度 | ⚠️ 需要API密钥 | ✅ 无需配置 |
| 成本 | ⚠️ 免费计划有限制 | ✅ 完全免费 |
| 访问限制 | ⚠️ 可能无法访问 | ✅ 通常可访问 |

## 建议

1. **优先使用RSS源**：RSS源通常是免费且可访问的
2. **NewsAPI作为补充**：如果NewsAPI可访问，可以作为RSS源的补充，提供更多新闻源
3. **混合使用**：程序支持同时使用NewsAPI和RSS源，获得最全面的信息

## 验证RSS源是否可用

运行以下Python代码测试RSS源：

```python
import feedparser

rss_feeds = [
    "https://finance.yahoo.com/rss/headline",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://feeds.reuters.com/reuters/businessNews",
]

for url in rss_feeds:
    try:
        feed = feedparser.parse(url)
        if feed.entries:
            print(f"✅ {url}: {len(feed.entries)} 篇文章")
        else:
            print(f"⚠️ {url}: 无文章")
    except Exception as e:
        print(f"❌ {url}: 错误 - {e}")
```

## 常见问题

### Q: RSS源搜索的新闻数量少怎么办？

A: 
- 增加RSS源数量（在config.py中添加）
- 调整搜索关键词以匹配更多文章
- 考虑使用代理访问NewsAPI作为补充

### Q: 某些RSS源无法访问怎么办？

A: 程序会自动跳过无法访问的RSS源，继续使用其他可用的源。这是正常行为。

### Q: 可以只用RSS源不用OpenAI吗？

A: 不可以。OpenAI API用于评估信息的置信度，这是核心功能。不过你可以：
- 修改代码，使用其他AI服务替代OpenAI
- 或者使用免费的本地AI模型（需要修改confidence_evaluator.py）

## 总结

**即使无法访问NewsAPI，程序仍然可以正常工作！**

只需要：
1. 配置OpenAI API密钥
2. 不配置NewsAPI密钥（或留空）
3. 运行程序，程序会自动使用RSS源

RSS源通常足够获取高质量的白银投资相关信息。
