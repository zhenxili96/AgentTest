# Bltcy（柏拉图AI）API 配置指南

## 为什么使用 Bltcy？

Bltcy（柏拉图AI）是一个一站式AI大模型API聚合平台，提供了多个优点：

1. **无需科学上网**：全球直连，无封号风险，请求速度是个人账号的1200倍
2. **无需模型权限**：直接使用最新模型，无需开发基础，一个API key全模型通用
3. **兼容OpenAI接口协议**：支持无缝对接所有模型到各种支持接口的应用
4. **价格远低于官方**：享受渠道优势，价格更优惠
5. **支持多种模型**：支持ChatGPT、Claude、Gemini等260多种全球顶尖AI模型
6. **100%保障隐私**：仅做API中转

## 获取 Bltcy API Key

1. 访问 [Bltcy 官网](https://bltcy.cn/) 或 [API文档](https://api.bltcy.ai/)
2. 注册账号
3. 创建新的 API Key
4. 复制 API Key

## 配置步骤

### 方式1：使用 Bltcy（推荐）

在 `.env` 文件中配置：

```env
# 使用Bltcy（推荐）
BLTCY_API_KEY=your-bltcy-api-key-here

# 或者指定提供商（可选）
AI_PROVIDER=bltcy
```

### 方式2：优先级自动选择

程序会自动选择（优先级从高到低）：
- 如果配置了 `BLTCY_API_KEY`，优先使用 Bltcy
- 如果配置了 `OPENROUTER_API_KEY`，使用 OpenRouter
- 如果只配置了 `OPENAI_API_KEY`，使用 OpenAI
- 如果都没配置，使用默认评估（置信度分数 0.5）

## 可用模型

Bltcy 支持多种模型，程序默认使用 `gpt-4o-mini`，但你可以在 `.env` 文件中配置其他模型：

```env
# 指定使用的模型
AI_MODEL=gpt-4o-mini  # 或其他支持的模型
```

### 推荐模型

- `gpt-4o-mini` - OpenAI 最经济的模型（默认）
- `gpt-3.5-turbo` - OpenAI 快速模型
- `gpt-4-mini` - OpenAI 中等性能模型
- `claude-3-haiku` - Anthropic 快速模型

### 查看所有可用模型

访问 Bltcy 官网或文档查看支持的模型列表。

## 修改使用的模型

### 方式1：通过环境变量（推荐）

在 `.env` 文件中配置：

```env
BLTCY_API_KEY=your-bltcy-api-key-here
AI_MODEL=gpt-3.5-turbo  # 修改为你想要的模型
```

### 方式2：在代码中修改

编辑 `confidence_evaluator.py`：

```python
if self.provider == "bltcy" and Config.BLTCY_API_KEY:
    # 修改这里的模型名称
    self.fallback_models = [
        "gpt-4o-mini",      # 修改为你想要的模型
        "gpt-3.5-turbo",
        # ... 其他备用模型
    ]
```

## 优势

1. **无需科学上网**：国内可直接访问，无需代理
2. **价格优惠**：比官方API更便宜
3. **兼容性好**：完全兼容OpenAI接口，无需修改代码
4. **速度快**：请求速度更快
5. **多模型支持**：一个API key支持多种模型

## 注意事项

1. **API Key格式**：Bltcy API Key 格式可能不同于OpenAI，请从官网获取正确的格式
2. **模型名称**：Bltcy 使用的模型名称通常与OpenAI相同（如 `gpt-4o-mini`），无需添加前缀
3. **兼容性**：代码使用 OpenAI SDK，但通过 `base_url` 指向 Bltcy API，完全兼容
4. **计费方式**：请参考 Bltcy 官网的计费说明

## 故障排除

### 如果遇到认证错误

1. 检查 API Key 是否正确
2. 确认 API Key 已复制完整
3. 检查 `.env` 文件中的配置是否正确
4. 确认 API Key 是否有效（未过期或被禁用）

### 如果遇到模型不存在错误

1. 检查模型名称是否正确
2. 访问 Bltcy 官网确认模型可用
3. 某些模型可能需要特殊权限或付费
4. 尝试使用默认模型 `gpt-4o-mini`

### 如果遇到网络错误

1. 检查网络连接
2. 确认 Bltcy API 服务是否正常
3. 查看 Bltcy 官网是否有服务公告

## 相关链接

- Bltcy 官网：https://bltcy.cn/
- API 文档：https://api.bltcy.ai/
- 使用教程：https://bltcy.cn/docs/

## 与其他API的对比

| 特性 | Bltcy | OpenRouter | OpenAI |
|------|-------|------------|--------|
| 需要科学上网 | ❌ 不需要 | ✅ 需要 | ✅ 需要 |
| 价格 | 💰 优惠 | 💰 较便宜 | 💰 较贵 |
| 模型数量 | 260+ | 400+ | 有限 |
| 兼容性 | ✅ OpenAI格式 | ✅ OpenAI格式 | ✅ 原生 |
| 国内访问 | ✅ 支持 | ❌ 需要代理 | ❌ 需要代理 |
