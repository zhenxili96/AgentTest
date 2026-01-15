# 快速开始指南

## 第一步：安装依赖

```bash
pip install -r requirements.txt
```

## 第二步：配置API密钥

创建 `.env` 文件（在项目根目录），内容如下：

```env
# OpenAI API配置（必须）
OPENAI_API_KEY=sk-your-openai-api-key-here

# NewsAPI配置（必须）
NEWS_API_KEY=your-newsapi-key-here

# 数据库配置（可选，默认使用SQLite）
DATABASE_URL=sqlite:///silver_investment.db

# 搜索配置（可选）
SEARCH_INTERVAL_MINUTES=30
MAX_ARTICLES_PER_SEARCH=50
MIN_CONFIDENCE_SCORE=0.7
```

### 如何获取API密钥

1. **OpenAI API密钥**：
   - 访问 https://platform.openai.com/api-keys
   - 注册/登录账号
   - 创建新的API密钥
   - 注意：需要付费账户，但可以使用免费额度

2. **NewsAPI密钥（可选）**：
   - ⚠️ 如果无法访问NewsAPI，可以跳过此步骤
   - 访问 https://newsapi.org/（可能需要代理）
   - 如果不配置，程序会使用RSS源（Yahoo Finance、CNBC等）
   - 详细说明请查看 `docs/NEWSAPI_ALTERNATIVE.md`

## 第三步：运行程序

### 方式1：自动定时搜索（推荐）

```bash
python main.py
```

程序将：
- 立即执行一次搜索
- 然后每30分钟自动搜索一次
- 按 Ctrl+C 退出

### 方式2：启动API服务

```bash
python app.py
```

然后在浏览器或使用curl访问：
- 健康检查：http://localhost:5000/api/health
- 获取文章：http://localhost:5000/api/articles?high_confidence=true
- 统计信息：http://localhost:5000/api/stats

## 第四步：查看结果

### 通过API查看

```bash
# 获取高置信度文章
curl http://localhost:5000/api/articles?high_confidence=true

# 获取统计信息
curl http://localhost:5000/api/stats
```

### 通过Python脚本查看

运行示例脚本：

```bash
python examples/example_usage.py
```

## 常见问题

### Q: 提示"缺少必要的配置项"
A: 检查 `.env` 文件是否存在，并且API密钥是否正确配置。

### Q: OpenAI API调用失败
A: 检查API密钥是否正确，账户是否有余额。可以尝试在代码中使用 `gpt-3.5-turbo` 替代 `gpt-4o-mini` 以降低成本。

### Q: NewsAPI返回错误
A: 免费计划有请求限制，如果超过限制会返回错误。可以：
- 增加搜索间隔时间
- 升级到付费计划
- 使用其他数据源

### Q: 数据库文件在哪里？
A: 默认情况下，SQLite数据库文件 `silver_investment.db` 会创建在项目根目录。

### Q: 如何修改搜索关键词？
A: 在 `.env` 文件中修改 `SEARCH_KEYWORDS` 参数，用逗号分隔多个关键词。

## 下一步

- 查看 `README.md` 了解完整功能
- 查看 `examples/example_usage.py` 了解代码示例
- 根据需要修改 `config.py` 中的配置
