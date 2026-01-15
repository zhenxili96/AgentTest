# 下一步操作指南

## ✅ 已完成
- [x] 项目代码创建完成
- [x] Python依赖包安装完成

## 📋 接下来需要做的

### 第一步：创建 `.env` 配置文件

1. 在项目根目录 `D:\dev\financial-agent` 创建一个新文件，命名为 `.env`
2. 复制以下内容到 `.env` 文件：

```env
# OpenAI API配置（必须）
OPENAI_API_KEY=sk-your-openai-api-key-here

# NewsAPI配置（可选，如果无法访问可以不配置）
# NEWS_API_KEY=your-newsapi-key-here

# 数据库配置（可选，默认使用SQLite）
DATABASE_URL=sqlite:///silver_investment.db

# 搜索配置（可选）
SEARCH_INTERVAL_MINUTES=30
MAX_ARTICLES_PER_SEARCH=50
MIN_CONFIDENCE_SCORE=0.7

# 搜索关键词（可选）
SEARCH_KEYWORDS=白银,silver,银价,银价走势,白银投资,现货白银,白银期货
```

**提示**：你也可以参考项目中的 `env_template.txt` 文件，将其重命名为 `.env` 并填入密钥。

### 第二步：获取API密钥

#### 1. OpenAI API密钥（必须）

- 访问：https://platform.openai.com/api-keys
- 注册/登录账号
- 创建新的API密钥
- 复制密钥，替换 `.env` 文件中的 `sk-your-openai-api-key-here`
- ⚠️ 注意：需要付费账户，但有免费额度可以试用

#### 2. NewsAPI密钥（可选）

- ⚠️ **注意**：如果无法访问NewsAPI网站，可以跳过此步骤
- 访问：https://newsapi.org/（可能需要代理）
- 注册免费账号并获取API密钥
- 如果不配置NewsAPI，程序会自动使用RSS源（Yahoo Finance、CNBC、Reuters等）
- 📖 详细说明请查看 `docs/NEWSAPI_ALTERNATIVE.md`

### 第三步：运行程序

配置好API密钥后，你可以选择以下方式运行：

#### 方式1：自动定时搜索（推荐用于生产环境）

在CMD或PowerShell中运行：
```cmd
python main.py
```

程序会：
- 立即执行一次搜索
- 每30分钟自动搜索一次
- 将所有高置信度信息保存到数据库
- 按 Ctrl+C 退出

#### 方式2：启动API服务（推荐用于开发测试）

在CMD或PowerShell中运行：
```cmd
python app.py
```

然后在浏览器访问：
- 健康检查：http://localhost:5000/api/health
- 获取文章：http://localhost:5000/api/articles?high_confidence=true
- 统计信息：http://localhost:5000/api/stats

#### 方式3：运行示例脚本（了解基本用法）

```cmd
python examples/example_usage.py
```

## 📝 注意事项

1. **API密钥安全**：
   - `.env` 文件已在 `.gitignore` 中，不会被提交到Git
   - 不要将API密钥分享给他人
   - 如果密钥泄露，请立即重新生成

2. **成本控制**：
   - OpenAI API调用会产生费用
   - 建议使用 `gpt-4o-mini` 模型（代码中已默认使用）
   - 可以根据需要调整搜索频率和文章数量

3. **测试建议**：
   - 先用示例脚本测试基本功能
   - 确认API密钥正确后再运行主程序
   - 监控API使用量，避免超出预算

## 🚀 快速测试

如果API密钥已配置，可以快速测试：

```cmd
python -c "from config import Config; print('配置验证:', Config.validate())"
```

如果返回 `True`，说明配置正确。

## 📚 更多信息

- 查看 `README.md` 了解完整功能
- 查看 `docs/QUICKSTART.md` 了解快速开始
- 查看 `docs/INSTALL.md` 了解安装问题
- 查看 `docs/TERMINAL_FIX.md` 了解终端问题

## ❓ 遇到问题？

- API密钥错误：检查密钥是否正确，是否有多余的空格
- OpenAI调用失败：检查账户余额和API密钥权限
- NewsAPI错误：检查是否超过免费配额（每天100次）
- 数据库错误：检查是否有写入权限
