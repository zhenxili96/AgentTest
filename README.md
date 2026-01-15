# 白银投资决策信息源AI工具

一个自动实时搜索网上高置信度信息的AI工具，专门为白银投资提供决策消息源。

## 功能特性

- 🔍 **多数据源搜索**：整合多个可靠的新闻和财经数据源
- 🤖 **AI置信度评估**：使用AI模型评估信息可信度和相关性
- ⏰ **实时监控**：自动定期搜索最新信息
- 💾 **数据存储**：持久化存储搜索结果和分析
- 📊 **数据可视化**：提供API接口查看和分析数据
- 📈 **股市行情辅助**：获取股市行情快照，用于辅助分析

## 安装

```bash
# 安装依赖
pip install -r requirements.txt

# 复制环境变量配置文件
cp .env.example .env

# 编辑.env文件，填入你的API密钥
```

## 配置

在`.env`文件中配置以下参数：

- `OPENAI_API_KEY`: OpenAI API密钥（必须，用于置信度评估）
- `NEWS_API_KEY`: NewsAPI密钥（可选，如果无法访问可以不配置，程序会使用RSS源）
- `ALPHA_VANTAGE_API_KEY`: Alpha Vantage API密钥（可选，用于股市行情数据）
- `STOCK_SYMBOLS`: 股市代码列表（可选，用逗号分隔，如 SPY,QQQ,DIA）
- `SEARCH_INTERVAL_MINUTES`: 搜索间隔（分钟）
- `MIN_CONFIDENCE_SCORE`: 最小置信度分数阈值（0-1）

**注意**：如果无法访问NewsAPI，程序仍然可以正常工作，会自动使用内置的RSS源。详见 `docs/NEWSAPI_ALTERNATIVE.md`

## 使用方法

### 方式1：运行主程序（推荐）

主程序会自动定期搜索和评估信息：

```bash
python main.py
```

程序会：
- 立即执行一次搜索
- 然后每30分钟（可配置）自动执行一次搜索
- 将所有高置信度的信息保存到数据库

### 方式2：运行API服务

启动Flask API服务，通过HTTP接口访问数据：

```bash
python app.py
```

API将在 `http://localhost:5000` 上运行。

### API接口说明

#### 1. 健康检查
```
GET /api/health
```

#### 2. 获取文章列表
```
GET /api/articles?high_confidence=true&limit=50&min_score=0.8
```

参数：
- `high_confidence`: 是否只返回高置信度文章（true/false）
- `limit`: 返回数量限制（默认50）
- `min_score`: 最小置信度分数（0-1）
- `hours`: 最近N小时的文章（默认24）

#### 3. 获取统计信息
```
GET /api/stats
```

#### 4. 手动触发搜索
```
POST /api/search
```

#### 5. 获取股市行情
```
GET /api/market/stock?symbols=SPY,QQQ,DIA
```

### 方式3：使用示例脚本

运行示例脚本了解基本用法：

```bash
python examples/example_usage.py
```

## 项目结构

```
financial-agent/
├── config.py              # 配置管理
├── database.py            # 数据库模型和操作
├── search_engine.py       # 信息搜索引擎
├── confidence_evaluator.py # AI置信度评估器
├── scheduler.py           # 定时任务调度器
├── keyword_miner.py       # 关键词挖掘器
├── main.py                # 主程序入口
├── app.py                 # Flask API服务
├── requirements.txt       # 依赖包列表
├── utils/                 # 工具函数
├── docs/                  # 文档目录
│   ├── INSTALL.md
│   ├── QUICKSTART.md
│   ├── KEYWORD_MINING.md
│   └── ...（其他文档）
├── examples/              # 示例代码
│   ├── example_usage.py
│   └── example_keyword_mining.py
├── templates/             # HTML模板
└── static/                # 静态资源
```

## 数据源

当前支持的数据源：
- **NewsAPI**：全球新闻聚合API
- **RSS Feeds**：财经网站RSS源（Yahoo Finance、CNBC、Reuters等）
- 可扩展：支持添加更多数据源

## 置信度评估

系统使用OpenAI GPT模型从三个维度评估信息：

1. **相关性（Relevance）**：文章与白银投资的关联程度
2. **可靠性（Reliability）**：信息来源的可信度
3. **置信度（Confidence）**：综合置信度，用于投资决策的参考价值

只有置信度分数达到阈值（默认0.7）的文章才会被标记为高置信度。

## 数据库

默认使用SQLite数据库（`silver_investment.db`），所有文章和分析结果都会持久化存储。

可以配置为使用PostgreSQL等数据库（修改`.env`中的`DATABASE_URL`）。

## 注意事项

1. **API密钥**：需要配置OpenAI API和NewsAPI密钥才能正常使用
2. **成本控制**：OpenAI API调用会产生费用，建议使用`gpt-4o-mini`模型以降低成本
3. **搜索频率**：根据实际需求调整搜索间隔，避免过于频繁的API调用
4. **数据准确性**：AI评估结果仅供参考，投资决策请结合多方信息

## 开发计划

- [ ] 支持更多数据源（Twitter、Reddit等）
- [ ] 添加数据可视化界面
- [ ] 支持邮件/通知推送高置信度信息
- [ ] 添加情感分析功能
- [ ] 支持多语言信息源

## 许可证

MIT License
