# OpenAI API 配额和计费说明

## 常见误解

**ChatGPT Plus 会员 ≠ OpenAI API 配额**

这是两个独立的服务：

### ChatGPT Plus
- 💰 价格：$20/月（订阅制）
- 🎯 用途：仅用于 ChatGPT 网页和移动应用界面
- ❌ **不能用于 API 调用**

### OpenAI API
- 💰 价格：按使用量付费（按 token 计费）
- 🎯 用途：通过 API 调用 OpenAI 模型
- ✅ 有免费试用额度（新用户通常 $5）
- ⚠️ 用完后需要充值才能继续使用

## 错误代码说明

### 429 - insufficient_quota（配额不足）

**错误信息：**
```
Error code: 429 - {'error': {'message': 'You exceeded your current quota, please check your plan and billing details.'}}
```

**原因：**
- API 账户的免费额度已用完
- 账户余额不足
- 需要充值或添加支付方式

**解决方案：**

1. **为 API 账户充值（推荐）**
   - 访问：https://platform.openai.com/account/billing
   - 添加支付方式（信用卡等）
   - 设置使用限制或充值（建议先充值 $5-10 试用）
   - 程序使用的 `gpt-4o-mini` 模型成本较低，$5 可以处理很多请求

2. **检查账户余额**
   - 访问：https://platform.openai.com/usage
   - 查看当前使用量和余额

3. **查看定价信息**
   - 访问：https://openai.com/api/pricing/
   - `gpt-4o-mini` 模型价格：输入 $0.15/1M tokens，输出 $0.60/1M tokens
   - 程序每次评估约使用 500-1000 tokens，成本很低

## 程序中的处理

程序已经处理了 API 错误情况：

- 如果 API 调用失败（包括配额不足），会使用默认评估
- 返回默认置信度分数（0.5）
- 程序继续运行，不会崩溃

## 成本估算

程序使用的配置：
- 模型：`gpt-4o-mini`（最经济的模型）
- 每次调用：约 500-1000 tokens
- 成本：约 $0.0005-0.001 每次评估

假设：
- 每次搜索找到 10 篇文章
- 每 30 分钟搜索一次
- 每天运行 24 小时

**日成本：** 约 $0.07-0.14（约 $2-4/月）

## 建议

1. **新用户**：先使用免费试用额度（$5）测试
2. **生产使用**：充值 $10-20 可以使用几个月
3. **预算控制**：在 OpenAI 控制台设置使用限制
4. **成本优化**：程序已使用最经济的模型（gpt-4o-mini）

## 相关链接

- OpenAI API 定价：https://openai.com/api/pricing/
- 账户余额：https://platform.openai.com/usage
- 账单设置：https://platform.openai.com/account/billing
- API 文档：https://platform.openai.com/docs/
