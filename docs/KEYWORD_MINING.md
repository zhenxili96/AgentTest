# 关键词挖掘Agent工具

## 功能概述

关键词挖掘Agent工具可以实时从市场数据中自动挖掘能引发白银价格波动的关键词，帮助您：

1. **自动发现新关键词**：从高置信度文章和市场趋势中识别可能影响白银价格的关键词
2. **智能分析相关性**：使用AI评估关键词与白银价格的关联程度和影响方向
3. **持续优化搜索**：动态更新关键词列表，提高信息搜索的覆盖率和准确性

## 核心功能

### 1. 从文章中挖掘关键词

分析数据库中高置信度的文章，提取关键词：

```python
from keyword_miner import KeywordMiner
from database import db

miner = KeywordMiner()

# 从高置信度文章中挖掘关键词
keywords = miner.mine_keywords_from_articles(
    hours=48,          # 分析最近48小时的文章
    min_confidence=0.7, # 最低置信度阈值
    limit=50           # 最多分析50篇文章
)

# 保存到数据库
for kw_data in keywords:
    db.add_mined_keyword(kw_data)
```

### 2. 从市场趋势中挖掘关键词

基于当前市场热点和趋势，预测可能影响白银价格的关键词：

```python
# 从市场趋势中挖掘关键词
keywords = miner.mine_keywords_from_market_trends(
    market_context="当前市场关注通胀数据和美联储政策"
)
```

### 3. 分析单个关键词

评估单个关键词与白银价格的相关性：

```python
# 分析关键词相关性
analysis = miner.analyze_keyword_relevance(
    keyword="美联储加息",
    context="美联储可能在下次会议加息"
)

print(f"相关性分数: {analysis['relevance_score']}")
print(f"影响方向: {analysis['impact']}")  # 上涨/下跌/中性/不确定
print(f"分析说明: {analysis['reasoning']}")
```

### 4. 获取建议关键词列表

获取经过筛选和排序的建议关键词列表：

```python
# 获取建议的关键词（可用于更新搜索配置）
suggested_keywords = miner.get_suggested_keywords(
    min_relevance=0.6,  # 最低相关性阈值
    max_results=50      # 最多返回50个
)
```

## API接口

### 1. 挖掘关键词

```http
POST /api/keywords/mine
Content-Type: application/json

{
    "source": "articles",      // "articles" 或 "trends"
    "hours": 48,               // 分析最近N小时的文章
    "min_confidence": 0.7,     // 最低置信度
    "limit": 50,               // 文章数量限制
    "market_context": "..."    // 可选：额外市场信息
}
```

响应：
```json
{
    "success": true,
    "mined": 15,
    "saved": 15,
    "keywords": [
        {
            "keyword": "美联储加息",
            "relevance_score": 0.9,
            "impact": "下跌",
            "reasoning": "...",
            "mined_at": "2024-01-01T12:00:00"
        }
    ]
}
```

### 2. 获取已挖掘的关键词

```http
GET /api/keywords?active=true&min_relevance=0.6&limit=100
```

参数：
- `active`: 是否只返回活跃的关键词（true/false）
- `min_relevance`: 最低相关性分数（0-1）
- `limit`: 返回数量限制

### 3. 分析单个关键词

```http
POST /api/keywords/analyze
Content-Type: application/json

{
    "keyword": "美联储加息",
    "context": "可选：上下文信息"
}
```

### 4. 获取建议的关键词列表

```http
GET /api/keywords/suggested?min_relevance=0.6&max_results=50
```

## 使用示例

### 方式1：使用Python脚本

运行示例脚本：

```bash
python examples/example_keyword_mining.py
```

### 方式2：通过API

使用curl或任何HTTP客户端：

```bash
# 挖掘关键词
curl -X POST http://localhost:5000/api/keywords/mine \
  -H "Content-Type: application/json" \
  -d '{"source": "articles", "hours": 48}'

# 获取建议关键词
curl http://localhost:5000/api/keywords/suggested?min_relevance=0.6
```

### 方式3：集成到现有代码

在调度器或主程序中集成关键词挖掘：

```python
from keyword_miner import KeywordMiner
from database import db

miner = KeywordMiner()

# 定期挖掘关键词（例如每天一次）
def mine_keywords_daily():
    # 从文章中挖掘
    keywords = miner.mine_keywords_from_articles()
    for kw_data in keywords:
        db.add_mined_keyword(kw_data)
    
    # 从趋势中挖掘
    keywords = miner.mine_keywords_from_market_trends()
    for kw_data in keywords:
        db.add_mined_keyword(kw_data)
```

## 数据库结构

关键词存储在 `mined_keywords` 表中：

- `id`: 主键
- `keyword`: 关键词
- `relevance_score`: 相关性分数（0-1）
- `impact`: 影响方向（上涨/下跌/中性/不确定）
- `reasoning`: AI分析说明
- `source`: 来源（ai_analysis, manual等）
- `is_active`: 是否启用
- `usage_count`: 使用次数
- `mined_at`: 挖掘时间
- `last_used_at`: 最后使用时间

## 配置要求

关键词挖掘功能需要配置AI API：

1. **OpenRouter API**（推荐）
   ```env
   OPENROUTER_API_KEY=sk-or-v1-your-key-here
   AI_PROVIDER=openrouter
   ```

2. **OpenAI API**
   ```env
   OPENAI_API_KEY=sk-your-key-here
   AI_PROVIDER=openai
   ```

## 最佳实践

1. **定期挖掘**：建议每天或每周运行一次关键词挖掘，保持关键词列表的时效性
2. **筛选阈值**：使用 `min_relevance=0.6` 或更高的阈值来过滤低相关性关键词
3. **人工审核**：虽然AI可以自动挖掘，但建议定期审查关键词，手动启用/禁用关键词
4. **结合使用**：将挖掘的关键词与现有关键词结合使用，扩大搜索覆盖范围
5. **监控使用**：关注关键词的使用次数，识别哪些关键词更有价值

## 注意事项

1. **API成本**：关键词挖掘会调用AI API，会产生一定的API调用费用
2. **数据依赖**：需要先有足够的高置信度文章，才能有效挖掘关键词
3. **关键词质量**：AI挖掘的关键词可能不完美，建议人工审核
4. **更新频率**：不建议过于频繁地挖掘关键词（例如每小时），建议每天或每周一次

## 工作流程

```
1. 收集高置信度文章
   ↓
2. AI分析文章内容
   ↓
3. 提取潜在关键词
   ↓
4. 评估关键词相关性
   ↓
5. 保存到数据库
   ↓
6. 可选：更新搜索关键词配置
```

## 故障排除

### 问题：挖掘不到关键词

- 检查是否有足够的高置信度文章（至少10篇）
- 检查AI API是否配置正确
- 尝试降低 `min_confidence` 阈值

### 问题：关键词质量不高

- 提高 `min_relevance` 阈值（例如0.7）
- 增加分析的文章数量（`limit`参数）
- 人工审核并禁用低质量关键词

### 问题：API调用失败

- 检查API密钥是否正确
- 检查网络连接
- 查看错误日志了解具体错误信息

## 相关文档

- `docs/KEYWORD_STRATEGY.md` - 关键词策略说明
- `examples/example_keyword_mining.py` - 使用示例代码
- `database.py` - 数据库模型和操作
