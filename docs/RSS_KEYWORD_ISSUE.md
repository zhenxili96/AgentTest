# RSS源关键词匹配问题说明

## 问题现象

程序可以成功访问RSS源（如CNBC、Bloomberg），获取到文章（如60篇），但没有文章匹配关键词，导致搜索结果为空。

## 根本原因

**通用财经RSS源的文章标题和摘要中很少包含"silver"、"precious metals"等特定关键词。**

这些RSS源（Yahoo Finance、CNBC、Reuters、Bloomberg等）主要提供：
- 股票市场新闻
- 经济政策新闻  
- 公司财报新闻
- 宏观经济分析

即使有关于贵金属的新闻，标题中也可能不直接包含"silver"等词。

## 解决方案

### 方案1：使用NewsAPI（推荐）

NewsAPI支持关键词搜索，可以找到包含特定关键词的文章。

**配置步骤：**
1. 访问 https://newsapi.org/ 获取API密钥（可能需要代理）
2. 在 `.env` 文件中配置：
   ```env
   NEWS_API_KEY=your-newsapi-key-here
   ```

### 方案2：调整关键词策略

#### 选项A：使用更通用的财经关键词
在 `.env` 文件中设置：
```env
SEARCH_KEYWORDS=finance,market,economy,investment,stock
```
**注意**：这会匹配大量文章，需要使用置信度评估来筛选相关内容。

#### 选项B：暂时移除关键词过滤（仅用于测试）
修改 `search_engine.py`，暂时注释掉关键词过滤逻辑，查看RSS源实际能获取多少文章。

### 方案3：添加专门的贵金属RSS源

如果找到专门的贵金属/商品RSS源，可以在 `config.py` 的 `RSS_FEEDS` 列表中添加。

## 当前系统设计

程序的设计思路是：
- **NewsAPI**：用于关键词搜索特定主题（如白银）
- **RSS源**：用于通用财经新闻监控

如果只使用RSS源，并且关键词过于具体，确实可能匹配不到文章。这是预期行为，不是bug。

## 建议

1. **如果专门搜索白银相关新闻**：使用NewsAPI（方案1）
2. **如果监控通用财经新闻**：使用更通用的关键词（方案2A）
3. **混合使用**：同时使用NewsAPI和RSS源，获得最全面的信息

## 验证方法

运行诊断脚本查看RSS源实际内容：
```bash
python diagnose_rss.py
```

这会显示RSS源获取的文章标题，帮助你了解实际内容，从而调整关键词策略。
