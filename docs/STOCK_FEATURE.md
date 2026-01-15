# 股票搜索与实时走势功能说明

## 功能概述

在原有系统基础上，新增了股票识别和实时走势展示功能。系统能够：
1. 从挖掘的关键词和高置信度文章中自动识别相关股票
2. 获取股票的实时价格和历史走势数据
3. 在Web界面上展示股票列表和实时走势图表

## 新增模块

### 1. stock_identifier.py - 股票识别模块
- **功能**：使用AI从关键词和文章中识别相关股票代码
- **主要方法**：
  - `identify_stocks_from_keywords()`: 从关键词列表中识别股票
  - `identify_stocks_from_articles()`: 从高置信度文章中识别股票

### 2. stock_fetcher.py - 股票数据获取模块
- **功能**：获取股票的实时价格和历史走势数据
- **主要方法**：
  - `fetch_realtime_price()`: 获取股票实时价格
  - `fetch_intraday_data()`: 获取股票日内数据（用于走势图）
  - `fetch_daily_data()`: 获取股票日线数据

### 3. 数据库扩展
在 `database.py` 中新增了两个数据模型：
- **IdentifiedStock**: 存储识别的股票信息
- **StockPrice**: 存储股票价格历史记录

## 新增API接口

### 1. 获取识别的股票列表
```
GET /api/stocks/identified?active=true&limit=50
```

### 2. 手动触发股票识别
```
POST /api/stocks/identify
Body: {
    "source": "keywords" | "articles",
    "theme": "白银"
}
```

### 3. 获取股票实时价格
```
GET /api/stocks/<symbol>/price
```

### 4. 获取股票走势图数据
```
GET /api/stocks/<symbol>/chart?type=daily&days=30
GET /api/stocks/<symbol>/chart?type=intraday&interval=5min
```

### 5. 获取股票价格历史
```
GET /api/stocks/<symbol>/history?hours=24&limit=100
```

### 6. 更新股票价格
```
POST /api/stocks/update
Body: {
    "symbols": "AAPL,MSFT"  // 可选，不提供则更新所有活跃股票
}
```

## 定时任务

在 `scheduler.py` 中新增了两个定时任务：
1. **股票识别任务**：每2小时执行一次，从关键词和文章中识别相关股票
2. **股票价格更新任务**：每30分钟执行一次，更新所有活跃股票的价格

## Web界面功能

### 新增"相关股票"标签页
- 显示所有识别的股票列表
- 显示每只股票的实时价格和涨跌幅
- 提供"识别股票"、"更新价格"、"查看走势"等操作按钮

### 股票走势图
- 点击"查看走势"按钮，弹出模态窗口显示股票走势图
- 支持日线图（默认30天）和日内图（5分钟间隔）
- 使用Canvas绘制价格走势曲线

## 使用流程

1. **自动识别**：
   - 系统每2小时自动从关键词和文章中识别相关股票
   - 识别的股票会自动保存到数据库

2. **手动识别**：
   - 在Web界面的"相关股票"标签页点击"识别股票"按钮
   - 可以选择从关键词或文章中识别

3. **查看股票**：
   - 在"相关股票"标签页查看所有识别的股票
   - 每只股票显示实时价格和涨跌幅

4. **查看走势**：
   - 点击股票的"查看走势"按钮
   - 在弹出的模态窗口中查看价格走势图

5. **更新价格**：
   - 系统每30分钟自动更新所有活跃股票的价格
   - 也可以手动点击"更新价格"按钮

## 配置要求

### Alpha Vantage API
需要配置 `ALPHA_VANTAGE_API_KEY` 环境变量才能获取股票数据。

获取API密钥：
1. 访问 https://www.alphavantage.co/support/#api-key
2. 注册账号并获取免费API密钥
3. 在 `.env` 文件中添加：`ALPHA_VANTAGE_API_KEY=your_api_key_here`

**注意**：Alpha Vantage免费版有API调用频率限制（每分钟5次，每天500次），建议：
- 不要过于频繁地更新股票价格
- 优先更新重要的股票
- 考虑使用付费版本以获得更高的调用限制

## 数据流程

```
关键词/文章 → AI识别 → 股票代码 → 保存到数据库
                                    ↓
                            定时更新价格
                                    ↓
                            保存价格历史
                                    ↓
                            Web界面展示
```

## 注意事项

1. **API限制**：Alpha Vantage免费版有调用频率限制，建议合理设置更新间隔
2. **股票代码格式**：目前主要支持美股代码（1-5个字母，如AAPL、MSFT）
3. **数据准确性**：股票价格数据来源于Alpha Vantage，仅供参考
4. **走势图**：走势图使用Canvas绘制，数据来源于Alpha Vantage API

## 未来改进方向

1. 支持更多股票市场（A股、港股等）
2. 添加更多技术指标（MA、MACD等）
3. 支持股票筛选和排序功能
4. 添加股票价格预警功能
5. 优化走势图显示效果（使用专业图表库如Chart.js）
